import Foundation

enum AppPaths {
    // Source setup owns --work-dir; keep spaces as one Process argument.
    static func sourceWorkDirectoryArguments(_ arguments: [String]) -> [String] {
        guard let index = arguments.firstIndex(of: "--work-dir"), index + 1 < arguments.count else { return [] }
        return ["--work-dir", arguments[index + 1]]
    }

    static let bundle = Bundle.main.bundleURL
    static let resources = Bundle.main.resourceURL ?? bundle
    static let packaged = FileManager.default.fileExists(atPath:resources.appendingPathComponent("app/install_bundle.py").path)
    static let scripts = packaged ? resources.appendingPathComponent("app") : bundle.deletingLastPathComponent()
    static let data: URL = {
        if let override = ProcessInfo.processInfo.environment["LINEAGE_DATA_DIR"] { return URL(fileURLWithPath:override,isDirectory:true) }
        if !packaged { return scripts }
        return FileManager.default.urls(for:.applicationSupportDirectory,in:.userDomainMask)[0].appendingPathComponent("Lineage II for macOS",isDirectory:true)
    }()
    static let config = data.appendingPathComponent("config.local.json")
    static let python = packaged ? resources.appendingPathComponent("Python/bin/python3") : URL(fileURLWithPath:"/usr/bin/python3")
    static let helper = packaged ? resources.appendingPathComponent("Payload/helpers/NativeLauncherWindow.exe") : scripts.appendingPathComponent(".build/NativeLauncherWindow.exe")
    static var environment: [String:String] {
        var env = ProcessInfo.processInfo.environment
        if packaged {
            for key in Array(env.keys) where key.hasPrefix("PYTHON") || key.hasPrefix("DYLD_") || key.hasPrefix("WINE") || key.hasPrefix("__PYVENV") { env.removeValue(forKey:key) }
            env["PATH"] = "/usr/bin:/bin:/usr/sbin:/sbin"
            env["PYTHONNOUSERSITE"] = "1"
            env["PYTHONDONTWRITEBYTECODE"] = "1"
        }
        env["PYTHONUNBUFFERED"] = "1"
        env["LINEAGE_DATA_DIR"] = data.path
        env["LINEAGE_RESOURCES_DIR"] = resources.path
        env["LINEAGE_PACKAGED"] = packaged ? "1" : "0"
        env["LINEAGE_APP_BUNDLE"] = bundle.path
        return env
    }
}
