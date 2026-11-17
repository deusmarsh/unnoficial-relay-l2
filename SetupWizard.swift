import AppKit
import Foundation
import Darwin

final class SetupDelegate: NSObject, NSApplicationDelegate, NSWindowDelegate {
    var window: NSWindow!
    let titleLabel = NSTextField(labelWithString:"Install Lineage II Launcher")
    let detail = NSTextField(wrappingLabelWithString:"Prepare the compatibility runtime and launcher in a separate folder. Your game account stays with the official launcher.")
    let steps = NSTextField(labelWithString:"1  Prepare runtime     2  Install launcher     3  Play")
    let progress = NSProgressIndicator()
    let primary = NSButton(title:"Get Started",target:nil,action:nil)
    let detailsButton = NSButton(checkboxWithTitle:"Show details",target:nil,action:nil)
    let scroll = NSScrollView()
    let outputView = NSTextView()
    var task: Process?
    var input: Pipe?
    var output: Pipe?
    var buffer = Data()
    var waiting = false
    var responseKind = "confirm"
    var finished = false
    var canLaunch = false
    let root = AppPaths.scripts

    func applicationDidFinishLaunching(_ notification: Notification) {
        if AppPaths.packaged,
           let data = try? Data(contentsOf:AppPaths.data.appendingPathComponent("config.prepared.json")),
           let config = try? JSONSerialization.jsonObject(with:data) as? [String:Any],
           let prefix = config["prefix"] as? String,
           FileManager.default.fileExists(atPath:prefix + "/drive_c/Program Files (x86)/Innova/4game_global/bin/Launcher.exe") {
            titleLabel.stringValue = "Finish launcher setup"
            detail.stringValue = "Inn.games is installed. Finish setup to connect it to this Mac app. Use this app from Applications instead of the Windows desktop shortcut."
            primary.title = "Finish Setup"
        }
        let menu = NSMenu(); let item = NSMenuItem(); menu.addItem(item)
        let submenu = NSMenu(); submenu.addItem(NSMenuItem(title:"Quit Setup",action:#selector(NSApplication.terminate(_:)),keyEquivalent:"q"))
        menu.setSubmenu(submenu,for:item); NSApp.mainMenu = menu
        window = NSWindow(contentRect:NSRect(x:0,y:0,width:680,height:430),styleMask:[.titled,.closable,.miniaturizable],backing:.buffered,defer:false)
        window.title = "Lineage II — Setup"; window.isReleasedWhenClosed = false; window.delegate = self
        titleLabel.font = .systemFont(ofSize:26,weight:.semibold)
        detail.font = .systemFont(ofSize:14); detail.maximumNumberOfLines = 8
        steps.font = .systemFont(ofSize:12,weight:.medium); steps.textColor = .secondaryLabelColor
        progress.style = .bar; progress.isIndeterminate = true; progress.isDisplayedWhenStopped = false
        primary.target = self; primary.action = #selector(continueSetup); primary.keyEquivalent = "\r"
        detailsButton.target = self; detailsButton.action = #selector(toggleDetails)
        outputView.isEditable = false; outputView.font = .monospacedSystemFont(ofSize:11,weight:.regular)
        scroll.documentView = outputView; scroll.hasVerticalScroller = true; scroll.borderType = .bezelBorder; scroll.isHidden = true
        let content = window.contentView!
        for view in [titleLabel,detail,steps,progress,primary,detailsButton,scroll] { view.translatesAutoresizingMaskIntoConstraints = false; content.addSubview(view) }
        NSLayoutConstraint.activate([
            titleLabel.topAnchor.constraint(equalTo:content.topAnchor,constant:32), titleLabel.leadingAnchor.constraint(equalTo:content.leadingAnchor,constant:32),titleLabel.trailingAnchor.constraint(equalTo:content.trailingAnchor,constant:-32),
            steps.topAnchor.constraint(equalTo:titleLabel.bottomAnchor,constant:20),steps.leadingAnchor.constraint(equalTo:titleLabel.leadingAnchor),
            detail.topAnchor.constraint(equalTo:steps.bottomAnchor,constant:24),detail.leadingAnchor.constraint(equalTo:titleLabel.leadingAnchor),detail.trailingAnchor.constraint(equalTo:titleLabel.trailingAnchor),
            progress.topAnchor.constraint(equalTo:detail.bottomAnchor,constant:20),progress.leadingAnchor.constraint(equalTo:titleLabel.leadingAnchor),progress.trailingAnchor.constraint(equalTo:titleLabel.trailingAnchor),
            primary.trailingAnchor.constraint(equalTo:content.trailingAnchor,constant:-32),primary.bottomAnchor.constraint(equalTo:content.bottomAnchor,constant:-24),primary.widthAnchor.constraint(greaterThanOrEqualToConstant:130),
            detailsButton.leadingAnchor.constraint(equalTo:titleLabel.leadingAnchor),detailsButton.centerYAnchor.constraint(equalTo:primary.centerYAnchor),
            scroll.leadingAnchor.constraint(equalTo:titleLabel.leadingAnchor),scroll.trailingAnchor.constraint(equalTo:titleLabel.trailingAnchor),scroll.topAnchor.constraint(equalTo:progress.bottomAnchor,constant:20),scroll.bottomAnchor.constraint(equalTo:primary.topAnchor,constant:-20)
        ])
        window.center();window.makeKeyAndOrderFront(nil);NSApp.activate(ignoringOtherApps:true)
    }
    @objc func toggleDetails() {
        let show = detailsButton.state == .on
        scroll.isHidden = !show
        window.setContentSize(NSSize(width:680,height:show ? 650 : 430))
    }
    @objc func continueSetup() {
        if finished {
            if canLaunch {
                let launch = Process();launch.executableURL = AppPaths.packaged ? Bundle.main.executableURL : AppPaths.python
                launch.arguments = AppPaths.packaged ? ["--launch","--finish-setup"] : [root.appendingPathComponent("start_native_frame_relay.py").path,"--new-instance","--finish-setup"]
                launch.environment = AppPaths.environment
                launch.currentDirectoryURL = AppPaths.data
                do { try launch.run(); NSApp.terminate(nil) } catch { detail.stringValue = "Could not open launcher. Use Start-4game-Relay.command." }
            } else { NSApp.terminate(nil) }
            return
        }
        if waiting {
            waiting = false;primary.isEnabled = false;progress.startAnimation(nil)
            let answer = responseKind == "confirm" ? "y\n" : "\n"
            input?.fileHandleForWriting.write(Data(answer.utf8))
            return
        }
        guard task == nil else { return }
        let process = Process();let stdinPipe = Pipe();let stdoutPipe = Pipe()
        process.executableURL = AppPaths.python
        process.arguments = [root.appendingPathComponent(AppPaths.packaged ? "install_bundle.py" : "install.py").path,"--gui"]
        if CommandLine.arguments.contains("--prepare-only") { process.arguments?.append("--prepare-only") }
        if !AppPaths.packaged { process.arguments?.append(contentsOf: AppPaths.sourceWorkDirectoryArguments(CommandLine.arguments)) }
        process.currentDirectoryURL = AppPaths.scripts
        process.environment = AppPaths.environment
        process.standardInput = stdinPipe;process.standardOutput = stdoutPipe;process.standardError = stdoutPipe
        input = stdinPipe;output = stdoutPipe;task = process
        primary.isEnabled = false;progress.startAnimation(nil)
        stdoutPipe.fileHandleForReading.readabilityHandler = { [weak self] handle in
            let data = handle.availableData
            DispatchQueue.main.async { self?.consume(data) }
        }
        process.terminationHandler = { [weak self] process in DispatchQueue.main.asyncAfter(deadline:.now()+0.2) {
            guard let self = self else { return }
            self.output?.fileHandleForReading.readabilityHandler = nil
            if !self.finished { self.showFailure("Setup stopped. Open details for the last message. You can rerun setup to resume.") }
        } }
        do { try process.run() } catch { showFailure("Could not start setup: " + error.localizedDescription) }
    }
    func consume(_ data: Data) {
        guard !data.isEmpty else { return }
        buffer.append(data)
        while let end = buffer.firstIndex(of:10) {
            let lineData = buffer.subdata(in:buffer.startIndex..<end);buffer.removeSubrange(buffer.startIndex...end)
            let line = String(decoding:lineData,as:UTF8.self)
            let marker = "@@LINEAGE_SETUP@@"
            if line.hasPrefix(marker),let json = line.dropFirst(marker.count).data(using:.utf8),let event = try? JSONSerialization.jsonObject(with:json) as? [String:Any] { apply(event) }
            else {
                outputView.textStorage?.append(NSAttributedString(string:line+"\n"))
                if outputView.string.count > 50000 { outputView.textStorage?.deleteCharacters(in:NSRange(location:0,length:10000)) }
                outputView.scrollToEndOfDocument(nil)
            }
        }
    }
    func apply(_ event: [String:Any]) {
        switch event["kind"] as? String {
        case "stage":
            titleLabel.stringValue = event["title"] as? String ?? "Preparing…"
            detail.stringValue = event["detail"] as? String ?? ""
        case "prompt":
            progress.stopAnimation(nil);waiting = true;responseKind = event["response"] as? String ?? "confirm"
            detail.stringValue = event["message"] as? String ?? "Continue?"
            primary.title = responseKind == "confirm" ? "Continue" : "I've Finished";primary.isEnabled = true
        case "complete":
            finished = true;canLaunch = event["launch"] as? Bool ?? false;progress.stopAnimation(nil)
            titleLabel.stringValue = event["title"] as? String ?? "Setup complete"
            detail.stringValue = event["detail"] as? String ?? ""
            primary.title = canLaunch ? "Open Launcher" : "Done";primary.isEnabled = true
        case "failed": showFailure(event["message"] as? String ?? "Setup stopped.")
        default: break
        }
    }
    func showFailure(_ message: String) {
        finished = true;canLaunch = false;progress.stopAnimation(nil)
        titleLabel.stringValue = "Setup needs attention";detail.stringValue = message
        primary.title = "Close";primary.isEnabled = true
    }
    func applicationShouldTerminate(_ sender: NSApplication) -> NSApplication.TerminateReply {
        if finished { return .terminateNow }
        guard let task = task,task.isRunning else { return .terminateNow }
        let alert = NSAlert();alert.messageText = "Stop setup?";alert.informativeText = "Completed downloads and builds are kept. The setup process and its build tasks will stop. Your previous installation is kept."
        alert.addButton(withTitle:"Keep Installing");alert.addButton(withTitle:"Stop Setup")
        if alert.runModal() == .alertFirstButtonReturn { return .terminateCancel }
        try? input?.fileHandleForWriting.close()
        if Darwin.kill(-task.processIdentifier, SIGTERM) != 0 { task.terminate() }
        return .terminateNow
    }
    func windowShouldClose(_ sender: NSWindow) -> Bool { NSApp.terminate(nil);return false }
    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { true }
}
