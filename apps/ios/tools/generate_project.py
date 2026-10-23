"""Regenerate the checked-in Xcode project. Python stdlib only; not required to open/build it."""
from hashlib import sha1
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "DubaiIO.xcodeproj"


def uid(name):
    return sha1(name.encode()).hexdigest()[:24].upper()


def quoted(value):
    return '"' + value.replace('\\', '\\\\').replace('"', '\\"') + '"'


def main():
    objects = []

    def obj(name, value):
        objects.append(f"\t\t{uid(name)} = {{ {value} }};")

    source_refs, source_builds = [], []
    for path in sorted((ROOT / "DubaiIO").glob("*.swift")):
        ref, build = "file:" + path.name, "build:" + path.name
        obj(ref, f"isa = PBXFileReference; lastKnownFileType = sourcecode.swift; path = {quoted(path.name)}; sourceTree = \"<group>\";")
        obj(build, f"isa = PBXBuildFile; fileRef = {uid(ref)};")
        source_refs.append(uid(ref))
        source_builds.append(uid(build))
    for name, kind in [("Assets.xcassets", "folder.assetcatalog"), ("Info-Debug.plist", "text.plist.xml"), ("Info-Release.plist", "text.plist.xml")]:
        obj("file:" + name, f"isa = PBXFileReference; lastKnownFileType = {kind}; path = {quoted(name)}; sourceTree = \"<group>\";")
        source_refs.append(uid("file:" + name))
    obj("resource:assets", f"isa = PBXBuildFile; fileRef = {uid('file:Assets.xcassets')};")
    obj("product", 'isa = PBXFileReference; explicitFileType = wrapper.application; includeInIndex = 0; path = DubaiIO.app; sourceTree = BUILT_PRODUCTS_DIR;')
    obj("package", 'isa = XCLocalSwiftPackageReference; relativePath = Core;')
    obj("package:product", f"isa = XCSwiftPackageProductDependency; package = {uid('package')}; productName = DubaiIOCore;")
    obj("package:build", f"isa = PBXBuildFile; productRef = {uid('package:product')};")
    obj("group:app", f"isa = PBXGroup; children = ({','.join(source_refs)},); path = DubaiIO; sourceTree = \"<group>\";")
    obj("group:products", f"isa = PBXGroup; children = ({uid('product')},); name = Products; sourceTree = \"<group>\";")
    obj("group:root", f"isa = PBXGroup; children = ({uid('group:app')},{uid('group:products')},); sourceTree = \"<group>\";")
    obj("phase:sources", f"isa = PBXSourcesBuildPhase; buildActionMask = 2147483647; files = ({','.join(source_builds)},); runOnlyForDeploymentPostprocessing = 0;")
    obj("phase:resources", f"isa = PBXResourcesBuildPhase; buildActionMask = 2147483647; files = ({uid('resource:assets')},); runOnlyForDeploymentPostprocessing = 0;")
    obj("phase:frameworks", f"isa = PBXFrameworksBuildPhase; buildActionMask = 2147483647; files = ({uid('package:build')},); runOnlyForDeploymentPostprocessing = 0;")
    for mode in ["Debug", "Release"]:
        debug = mode == "Debug"
        settings = {
            "SDKROOT": "iphoneos", "IPHONEOS_DEPLOYMENT_TARGET": "26.0", "SWIFT_VERSION": "6.0",
            "CLANG_ENABLE_MODULES": "YES", "SWIFT_OPTIMIZATION_LEVEL": "-Onone" if debug else "-O",
            "DEBUG_INFORMATION_FORMAT": "dwarf" if debug else "dwarf-with-dsym",
        }
        obj("config:project:" + mode, "isa = XCBuildConfiguration; buildSettings = {" + " ".join(f"{k} = {quoted(v)};" for k, v in settings.items()) + f"}}; name = {mode};")
        settings = {
            "PRODUCT_BUNDLE_IDENTIFIER": "com.dubaiio.companion.dev", "PRODUCT_NAME": "$(TARGET_NAME)",
            "GENERATE_INFOPLIST_FILE": "NO", "INFOPLIST_FILE": f"DubaiIO/Info-{mode}.plist",
            "TARGETED_DEVICE_FAMILY": "1", "SUPPORTED_PLATFORMS": "iphoneos iphonesimulator",
            "CODE_SIGN_STYLE": "Automatic", "CURRENT_PROJECT_VERSION": "1", "MARKETING_VERSION": "0.1.0",
            "ASSETCATALOG_COMPILER_GLOBAL_ACCENT_COLOR_NAME": "AccentColor", "ENABLE_PREVIEWS": "YES",
            "SWIFT_EMIT_LOC_STRINGS": "YES", "SWIFT_ACTIVE_COMPILATION_CONDITIONS": "DEBUG" if debug else "",
        }
        obj("config:app:" + mode, "isa = XCBuildConfiguration; buildSettings = {" + " ".join(f"{k} = {quoted(v)};" for k, v in settings.items()) + f"}}; name = {mode};")
    for kind in ["project", "app"]:
        obj("configs:" + kind, f"isa = XCConfigurationList; buildConfigurations = ({uid('config:' + kind + ':Debug')},{uid('config:' + kind + ':Release')},); defaultConfigurationIsVisible = 0; defaultConfigurationName = Release;")
    obj("target", f"isa = PBXNativeTarget; buildConfigurationList = {uid('configs:app')}; buildPhases = ({uid('phase:sources')},{uid('phase:frameworks')},{uid('phase:resources')},); buildRules = (); dependencies = (); name = DubaiIO; packageProductDependencies = ({uid('package:product')},); productName = DubaiIO; productReference = {uid('product')}; productType = \"com.apple.product-type.application\";")
    obj("project", f"isa = PBXProject; attributes = {{ BuildIndependentTargetsInParallel = YES; LastUpgradeCheck = 2600; }}; buildConfigurationList = {uid('configs:project')}; compatibilityVersion = \"Xcode 14.0\"; developmentRegion = en; hasScannedForEncodings = 0; knownRegions = (en,Base,); mainGroup = {uid('group:root')}; packageReferences = ({uid('package')},); productRefGroup = {uid('group:products')}; projectDirPath = \"\"; projectRoot = \"\"; targets = ({uid('target')},);")
    PROJECT.mkdir(exist_ok=True)
    (PROJECT / "project.pbxproj").write_text("// !$*UTF8*$!\n{\n\tarchiveVersion = 1;\n\tclasses = {};\n\tobjectVersion = 56;\n\tobjects = {\n" + "\n".join(objects) + f"\n\t}};\n\trootObject = {uid('project')};\n}}\n", encoding="utf-8")
    ref = f'<BuildableReference BuildableIdentifier="primary" BlueprintIdentifier="{uid("target")}" BuildableName="DubaiIO.app" BlueprintName="DubaiIO" ReferencedContainer="container:DubaiIO.xcodeproj"/>'
    scheme = f'''<?xml version="1.0" encoding="UTF-8"?>
<Scheme LastUpgradeVersion="2600" version="1.3">
  <BuildAction parallelizeBuildables="YES" buildImplicitDependencies="YES"><BuildActionEntries><BuildActionEntry buildForTesting="YES" buildForRunning="YES" buildForProfiling="YES" buildForArchiving="YES" buildForAnalyzing="YES">{ref}</BuildActionEntry></BuildActionEntries></BuildAction>
  <TestAction buildConfiguration="Debug" selectedDebuggerIdentifier="Xcode.DebuggerFoundation.Debugger.LLDB" selectedLauncherIdentifier="Xcode.IDEFoundation.Launcher.LLDB" shouldUseLaunchSchemeArgsEnv="YES"><Testables/></TestAction>
  <LaunchAction buildConfiguration="Debug" selectedDebuggerIdentifier="Xcode.DebuggerFoundation.Debugger.LLDB" selectedLauncherIdentifier="Xcode.IDEFoundation.Launcher.LLDB" launchStyle="0" useCustomWorkingDirectory="NO" ignoresPersistentStateOnLaunch="NO" debugDocumentVersioning="YES" debugServiceExtension="internal" allowLocationSimulation="YES"><BuildableProductRunnable runnableDebuggingMode="0">{ref}</BuildableProductRunnable></LaunchAction>
  <ProfileAction buildConfiguration="Release" shouldUseLaunchSchemeArgsEnv="YES" savedToolIdentifier="" useCustomWorkingDirectory="NO" debugDocumentVersioning="YES"><BuildableProductRunnable runnableDebuggingMode="0">{ref}</BuildableProductRunnable></ProfileAction>
  <AnalyzeAction buildConfiguration="Debug"/>
  <ArchiveAction buildConfiguration="Release" revealArchiveInOrganizer="YES"/>
</Scheme>
'''
    schemes = PROJECT / "xcshareddata" / "xcschemes"
    schemes.mkdir(parents=True, exist_ok=True)
    (schemes / "DubaiIO.xcscheme").write_text(scheme, encoding="utf-8")
    print(f"Generated {len(source_builds)} Swift source entries and shared DubaiIO scheme.")


if __name__ == "__main__":
    main()
