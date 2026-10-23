import Foundation

/// Screenshot harness, DEBUG builds only (`tools/screens.sh`).
/// `-screen intro|home|chat|services|feed|ask|me|maps` opens that screen at launch and
/// skips the notification prompt. Pair with `-apiAddress <url>` and
/// `-hasSeenNativeIntro YES`, which UserDefaults reads from launch arguments.
enum DebugLaunch {
    static var screen: String? {
        #if DEBUG
        UserDefaults.standard.string(forKey: "screen")
        #else
        nil
        #endif
    }
}
