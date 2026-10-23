// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "DubaiIOCore",
    platforms: [.iOS("26.0"), .macOS(.v15)],
    products: [.library(name: "DubaiIOCore", targets: ["DubaiIOCore"])],
    targets: [
        .target(name: "DubaiIOCore"),
        .testTarget(name: "DubaiIOCoreTests", dependencies: ["DubaiIOCore"])
    ]
)
