import AppKit
import Foundation

final class RelayCanvas: NSView {
    var frameImage: NSImage? { didSet { needsDisplay = true } }
    var frameNumber = 0
    private var lastDrawn = 0
    private(set) var drawnFrames = 0
    var viewportSize: NSSize?
    var emit: ((String, [String: Any]) -> Void)?
    var pressed = 0
    override var isFlipped: Bool { true }
    override var acceptsFirstResponder: Bool { true }
    override func updateTrackingAreas() {
        super.updateTrackingAreas()
        for area in trackingAreas { removeTrackingArea(area) }
        addTrackingArea(NSTrackingArea(rect: bounds, options: [.mouseMoved, .activeInKeyWindow, .inVisibleRect], owner: self))
    }
    var imageRect: NSRect {
        guard let size = frameImage?.size, size.width > 0, size.height > 0 else { return bounds }
        let factor = min(bounds.width / size.width, bounds.height / size.height)
        let width = size.width * factor, height = size.height * factor
        return NSRect(x: (bounds.width-width)/2, y: (bounds.height-height)/2, width: width, height: height)
    }
    override func draw(_ dirtyRect: NSRect) {
        NSColor.black.setFill(); bounds.fill()
        frameImage?.draw(in: imageRect, from: .zero, operation: .sourceOver, fraction: 1, respectFlipped: true, hints: nil)
        if frameImage != nil && frameNumber != lastDrawn {
            drawnFrames += 1
            lastDrawn = frameNumber
        }
    }
    func modifiers(_ event: NSEvent) -> Int {
        let flags = event.modifierFlags
        return (flags.contains(.option) ? 1 : 0) | ((flags.contains(.control) || flags.contains(.command)) ? 2 : 0) | (flags.contains(.shift) ? 8 : 0)
    }
    func pointer(_ event: NSEvent, type: String, button: String = "none", mask: Int = 0) {
        guard let size = frameImage?.size else { return }
        let rect = imageRect, point = convert(event.locationInWindow, from: nil)
        guard rect.width > 0, rect.height > 0, rect.contains(point) || pressed != 0 || type == "mouseReleased" else { return }
        var params: [String: Any] = ["type": type, "x": (point.x-rect.minX)*(viewportSize ?? size).width/rect.width, "y": (point.y-rect.minY)*(viewportSize ?? size).height/rect.height, "modifiers": modifiers(event), "buttons": pressed]
        if button != "none" { params["button"] = button; params["clickCount"] = event.clickCount }
        if type == "mouseWheel" {
            let factor: CGFloat = event.hasPreciseScrollingDeltas ? 1 : 40
            params["deltaX"] = -event.scrollingDeltaX * factor
            params["deltaY"] = -event.scrollingDeltaY * factor
        }
        emit?("Input.dispatchMouseEvent", params)
    }
    override func mouseDown(with e: NSEvent) { window?.makeFirstResponder(self); pressed |= 1; pointer(e, type: "mousePressed", button: "left") }
    override func mouseUp(with e: NSEvent) { pressed &= ~1; pointer(e, type: "mouseReleased", button: "left") }
    override func rightMouseDown(with e: NSEvent) { pressed |= 2; pointer(e, type: "mousePressed", button: "right") }
    override func rightMouseUp(with e: NSEvent) { pressed &= ~2; pointer(e, type: "mouseReleased", button: "right") }
    override func otherMouseDown(with e: NSEvent) { pressed |= 4; pointer(e, type: "mousePressed", button: "middle") }
    override func otherMouseUp(with e: NSEvent) { pressed &= ~4; pointer(e, type: "mouseReleased", button: "middle") }
    override func mouseMoved(with e: NSEvent) { pointer(e, type: "mouseMoved") }
    override func mouseDragged(with e: NSEvent) { pointer(e, type: "mouseMoved", button: "left") }
    override func rightMouseDragged(with e: NSEvent) { pointer(e, type: "mouseMoved", button: "right") }
    override func scrollWheel(with e: NSEvent) { pointer(e, type: "mouseWheel") }
    override func performKeyEquivalent(with event: NSEvent) -> Bool {
        if event.modifierFlags.contains(.command) {
            if event.keyCode == 12 { NSApp.terminate(nil); return true }
            if event.keyCode == 13 { window?.performClose(nil); return true }
            if event.keyCode == 37 { (NSApp.delegate as? RelayDelegate)?.showRuntimeLog(); return true }
            keyDown(with:event); return true
        }
        return super.performKeyEquivalent(with:event)
    }
    override func keyDown(with event: NSEvent) {
        if event.modifierFlags.contains(.command), event.keyCode == 9 {
            if let text = NSPasteboard.general.string(forType: .string) { emit?("Input.insertText", ["text": text]) }
            return
        }
        let special: [UInt16: (String, String, Int)] = [36:("Enter","Enter",13), 48:("Tab","Tab",9), 51:("Backspace","Backspace",8), 53:("Escape","Escape",27), 117:("Delete","Delete",46), 123:("ArrowLeft","ArrowLeft",37), 124:("ArrowRight","ArrowRight",39), 125:("ArrowDown","ArrowDown",40), 126:("ArrowUp","ArrowUp",38), 115:("Home","Home",36), 119:("End","End",35), 116:("PageUp","PageUp",33), 121:("PageDown","PageDown",34)]
        if let (key, code, virtual) = special[event.keyCode] {
            sendKey(key, code: code, virtual: virtual, event: event)
        } else if event.modifierFlags.contains(.command) || event.modifierFlags.contains(.control) {
            let letters: [UInt16: Int] = [0:65,11:66,8:67,2:68,14:69,3:70,5:71,4:72,34:73,38:74,40:75,37:76,46:77,45:78,31:79,35:80,12:81,15:82,1:83,17:84,32:85,9:86,13:87,7:88,16:89,6:90]
            if let virtual = letters[event.keyCode], let scalar = UnicodeScalar(virtual) {
                let text = String(scalar)
                sendKey(text.lowercased(), code:"Key" + text, virtual:virtual, event:event)
            }
        } else if let text = event.characters, !text.isEmpty {
            emit?("Input.insertText", ["text": text])
        }
    }
    func sendKey(_ key: String, code: String, virtual: Int, event: NSEvent) {
        var params: [String: Any] = ["type":"rawKeyDown", "key":key, "code":code, "windowsVirtualKeyCode":virtual, "modifiers":modifiers(event)]
        emit?("Input.dispatchKeyEvent", params)
        params["type"] = "keyUp"; emit?("Input.dispatchKeyEvent", params)
    }
}

final class RelayWindowController: NSObject, NSWindowDelegate {
    let target: [String:Any]
    let targetID: String
    let isChild: Bool
    let onClosed: (String) -> Void
    var window: NSWindow!
    let canvas = RelayCanvas()
    let status = NSTextField(labelWithString: "Connecting to launcher…")
    let session = URLSession(configuration: .ephemeral)
    var socket: URLSessionWebSocketTask?
    var nextID = 0
    var callbacks: [Int: ([String:Any]) -> Void] = [:]
    var timer: Timer?
    var capturing = false
    var stopped = false
    var displayed = 0
    var reconnectTimer: Timer?
    var windowHelper: Process?
    var lastCapture = Date.distantPast
    let smooth = NSButton(checkboxWithTitle: "Smooth", target: nil, action: nil)
    var fpsStart = ProcessInfo.processInfo.systemUptime
    var fpsStartFrames = 0
    var canvasAspect: CGFloat = 1
    var lastImageSize = NSSize.zero

    init(target: [String:Any], onClosed: @escaping (String) -> Void) {
        self.target = target
        self.targetID = target["id"] as? String ?? ""
        let path = URL(string:target["url"] as? String ?? "")?.path ?? ""
        self.isChild = path.hasPrefix("/window/")
        self.onClosed = onClosed
        super.init()
        openWindow(path:path)
    }
    func openWindow(path: String) {
        window = NSWindow(contentRect: NSRect(x:0,y:0,width:715,height:isChild ? 694 : 808), styleMask:[.titled,.closable,.miniaturizable,.resizable], backing:.buffered, defer:false)
        window.isReleasedWhenClosed = false
        window.title = path.hasPrefix("/window/install/") ? "Lineage II — Install" : isChild ? "Launcher — Additional window" : "Lineage II Launcher"
        window.contentMinSize = NSSize(width:420,height:260)
        window.delegate = self
        status.font = .systemFont(ofSize:12)
        status.textColor = .secondaryLabelColor
        status.maximumNumberOfLines = 2
        let root = NSView(); window.contentView = root
        let reload = NSButton(title:"Reload",target:self,action:#selector(reloadPage))
        reload.toolTip = "Reload launcher page and reconnect. The game is not restarted."
        smooth.state = .on
        smooth.target = self
        smooth.action = #selector(updateCaptureMode)
        smooth.toolTip = "Compare faster JPEG updates with the original PNG mode."
        for view in [status,smooth,reload,canvas] { view.translatesAutoresizingMaskIntoConstraints = false; root.addSubview(view) }
        NSLayoutConstraint.activate([status.leadingAnchor.constraint(equalTo:root.leadingAnchor,constant:12),status.trailingAnchor.constraint(lessThanOrEqualTo:smooth.leadingAnchor,constant:-8),smooth.trailingAnchor.constraint(equalTo:reload.leadingAnchor,constant:-8),smooth.centerYAnchor.constraint(equalTo:status.centerYAnchor),reload.trailingAnchor.constraint(equalTo:root.trailingAnchor,constant:-12),reload.centerYAnchor.constraint(equalTo:status.centerYAnchor),reload.widthAnchor.constraint(equalToConstant:80),status.topAnchor.constraint(equalTo:root.topAnchor,constant:8),status.heightAnchor.constraint(equalToConstant:32),canvas.leadingAnchor.constraint(equalTo:root.leadingAnchor),canvas.trailingAnchor.constraint(equalTo:root.trailingAnchor),canvas.topAnchor.constraint(equalTo:status.bottomAnchor,constant:4),canvas.bottomAnchor.constraint(equalTo:root.bottomAnchor)])
        canvas.emit = { [weak self] method, params in
            if method == "Input.dispatchMouseEvent", params["type"] as? String == "mousePressed" { self?.prepareWindowedGameIfNeeded() }
            self?.send(method, params)
        }
        window.center(); window.makeKeyAndOrderFront(nil); window.makeFirstResponder(canvas)
        NSApp.activate(ignoringOtherApps:true)
        connect()
    }
    func prepareWindowedGameIfNeeded() {
        guard !attachOnly else { return }
        let root = AppPaths.scripts
        guard let data = try? Data(contentsOf:AppPaths.config),
              let config = try? JSONSerialization.jsonObject(with:data) as? [String:Any],
              let prefix = config["prefix"] as? String else { return }
        let options = URL(fileURLWithPath:(prefix as NSString).expandingTildeInPath).appendingPathComponent("drive_c/Games/LineageII EU/system/Option.ini")
        guard FileManager.default.fileExists(atPath:options.path),
              !FileManager.default.fileExists(atPath:options.path + ".before-windowed.bak") else { return }
        let task = Process();task.executableURL = AppPaths.python
        task.arguments = [root.appendingPathComponent("configure_game_window.py").path]
        task.environment = AppPaths.environment
        task.currentDirectoryURL = AppPaths.data;task.standardOutput = FileHandle.nullDevice;task.standardError = FileHandle.nullDevice
        do { try task.run(); task.waitUntilExit() } catch { status.stringValue = "Could not apply windowed preferences." }
    }
    func minimizeOriginalWindow() {
        guard !isChild, !attachOnly else { return }
        let root = AppPaths.scripts
        guard FileManager.default.fileExists(atPath:AppPaths.helper.path) else { return }
        let task = Process(); task.executableURL = AppPaths.python
        task.arguments = [root.appendingPathComponent("launcher_window.py").path,"--hide"]
        task.environment = AppPaths.environment
        task.currentDirectoryURL = AppPaths.data
        task.standardOutput = FileHandle.nullDevice; task.standardError = FileHandle.nullDevice
        windowHelper = task
        try? task.run()
    }
    @objc func reloadPage() {
        status.stringValue = "Reloading launcher…"
        if socket != nil { send("Page.reload", ["ignoreCache":false]) }
        DispatchQueue.main.asyncAfter(deadline:.now()+1) { [weak self] in self?.fail("Reload requested.") }
    }
    func connect() {
        guard !stopped else { return }
        reconnectTimer?.invalidate(); reconnectTimer = nil
        guard let text = target["webSocketDebuggerUrl"] as? String, let url = URL(string:text), url.scheme == "ws", ["127.0.0.1","localhost"].contains(url.host ?? ""), url.port == 8088 else { fail("Invalid local launcher address."); return }
        socket = session.webSocketTask(with:url); socket?.maximumMessageSize = 32 * 1024 * 1024; socket?.resume(); receive()
        updateCaptureMode()
        send("Page.getLayoutMetrics", [:]) { [weak self] response in
            guard let result = response["result"] as? [String:Any],
                  let viewport = (result["cssLayoutViewport"] ?? result["layoutViewport"]) as? [String:Any],
                  let width = viewport["clientWidth"] as? Double,
                  let height = viewport["clientHeight"] as? Double, width > 0, height > 0 else { return }
            self?.canvas.viewportSize = NSSize(width:width,height:height)
        }
        capture()
    }
    func send(_ method: String, _ params: [String:Any], completion: (([String:Any]) -> Void)? = nil) {
        guard !stopped, let socket = socket else { return }
        nextID += 1; let ident = nextID
        if let completion = completion { callbacks[ident] = completion }
        guard let data = try? JSONSerialization.data(withJSONObject:["id":ident,"method":method,"params":params]), let text = String(data:data,encoding:.utf8) else { return }
        socket.send(.string(text)) { [weak self] error in
            if let error = error { DispatchQueue.main.async { self?.fail("Launcher disconnected (\((error as NSError).code)).") } }
        }
    }
    func receive() {
        socket?.receive { [weak self] result in
            DispatchQueue.main.async {
                guard let self = self, !self.stopped else { return }
                switch result {
                case .failure(let error): self.fail("Launcher disconnected (\((error as NSError).code)).")
                case .success(let message):
                    let data: Data?
                    switch message { case .string(let text): data = text.data(using:.utf8); case .data(let bytes): data = bytes; @unknown default: data = nil }
                    if let data = data, let object = try? JSONSerialization.jsonObject(with:data) as? [String:Any], let ident = object["id"] as? Int {
                        self.callbacks.removeValue(forKey:ident)?(object)
                    }
                    self.receive()
                }
            }
        }
    }
    @objc func updateCaptureMode() {
        timer?.invalidate()
        fpsStart = ProcessInfo.processInfo.systemUptime
        fpsStartFrames = canvas.drawnFrames
        let interval = smooth.state == .on ? 1.0 / 24 : 0.25
        let clock = Timer(timeInterval: interval, repeats: true) { [weak self] _ in
            guard let self = self else { return }
            self.capture()
            let now = ProcessInfo.processInfo.systemUptime
            if now - self.fpsStart >= 3 && self.displayed > 0 {
                let fps = Double(self.canvas.drawnFrames - self.fpsStartFrames) / (now - self.fpsStart)
                self.status.stringValue = String(format: "Launcher · %.1f FPS", fps)
                self.fpsStart = now
                self.fpsStartFrames = self.canvas.drawnFrames
            }
        }
        timer = clock
        RunLoop.main.add(clock, forMode: .common)
    }
    func capture() {
        guard !capturing, !stopped, window.isVisible, !window.isMiniaturized else { return }
        if !window.isKeyWindow && Date().timeIntervalSince(lastCapture) < 0.75 { return }
        lastCapture = Date(); capturing = true
        let options: [String:Any] = smooth.state == .on
            ? ["format":"jpeg", "quality":85, "fromSurface":true]
            : ["format":"png", "fromSurface":true]
        send("Page.captureScreenshot",options) { [weak self] response in
            guard let self = self else { return }; self.capturing = false
            guard let result = response["result"] as? [String:Any], let encoded = result["data"] as? String, let data = Data(base64Encoded:encoded), let image = NSImage(data:data) else { self.fail("Frame unavailable."); return }
            if self.displayed == 0 { self.minimizeOriginalWindow() }
            if image.size != self.lastImageSize {
                self.lastImageSize = image.size
                self.canvasAspect = image.size.width / max(1,image.size.height)
                let screen = (self.window.screen ?? NSScreen.main)?.visibleFrame.size ?? NSSize(width:1440,height:900)
                let factor = min(1, min((screen.width - 64) / image.size.width, (screen.height - 110) / image.size.height))
                let width = image.size.width * factor, height = image.size.height * factor
                self.window.contentMinSize = NSSize(width:280,height:280/self.canvasAspect+44)
                self.window.setContentSize(NSSize(width:width,height:height+44))
                self.window.center()
                self.send("Page.getLayoutMetrics", [:]) { [weak self] response in
                    guard let result = response["result"] as? [String:Any],
                          let viewport = (result["cssLayoutViewport"] ?? result["layoutViewport"]) as? [String:Any],
                          let width = viewport["clientWidth"] as? Double, let height = viewport["clientHeight"] as? Double else { return }
                    self?.canvas.viewportSize = NSSize(width:width,height:height)
                }
            }
            self.displayed += 1
            self.canvas.frameNumber = self.displayed
            self.canvas.frameImage = image
            if self.displayed == 1 { self.status.stringValue = "Connected to official launcher" }
        }
    }
    func fail(_ message: String) {
        guard !stopped, reconnectTimer == nil else { return }
        timer?.invalidate(); timer = nil; capturing = false; callbacks.removeAll()
        status.stringValue = message + " Reconnecting…"
        socket?.cancel(with:.goingAway,reason:nil); socket = nil
        reconnectTimer = Timer.scheduledTimer(withTimeInterval:2,repeats:false) { [weak self] _ in self?.connect() }
    }
    func windowWillResize(_ sender: NSWindow, to frameSize: NSSize) -> NSSize {
        guard displayed > 0 else { return frameSize }
        let chrome = sender.frame.height - sender.contentRect(forFrameRect:sender.frame).height
        return NSSize(width:frameSize.width,height:frameSize.width/canvasAspect+44+chrome)
    }
    func windowWillUseStandardFrame(_ window: NSWindow, defaultFrame newFrame: NSRect) -> NSRect {
        let chrome = window.frame.height - window.contentRect(forFrameRect:window.frame).height
        let width = min(newFrame.width, (newFrame.height-chrome-44)*canvasAspect)
        return NSRect(x:newFrame.midX-width/2,y:newFrame.minY,width:width,height:width/canvasAspect+44+chrome)
    }
    func shutdownTransport() { stopped = true; reconnectTimer?.invalidate(); timer?.invalidate(); socket?.cancel(with:.goingAway,reason:nil); session.invalidateAndCancel() }
    func windowWillClose(_ notification: Notification) { shutdownTransport(); onClosed(targetID) }
}

final class RuntimeConsole: NSObject {
    var window: NSWindow?
    let status = NSTextField(wrappingLabelWithString:"Starting the official launcher…")
    let text = NSTextView()
    var timer: Timer?
    var lastText = ""
    func show() {
        if window == nil {
            let panel = NSWindow(contentRect:NSRect(x:0,y:0,width:700,height:380),styleMask:[.titled,.closable,.miniaturizable,.resizable],backing:.buffered,defer:false)
            panel.title = "Lineage II — Runtime Log"; panel.isReleasedWhenClosed = false
            panel.contentMinSize = NSSize(width:460,height:280)
            let note = NSTextField(wrappingLabelWithString:"Windows compatibility services run in the background. This console shows their log. Closing this window keeps the launcher and game running.")
            note.font = .systemFont(ofSize:12); note.textColor = .secondaryLabelColor
            status.font = .systemFont(ofSize:13,weight:.medium)
            text.isEditable = false; text.font = .monospacedSystemFont(ofSize:11,weight:.regular)
            let scroll = NSScrollView(); scroll.documentView = text; scroll.hasVerticalScroller = true; scroll.borderType = .bezelBorder
            let content = panel.contentView!
            for view in [status,note,scroll] { view.translatesAutoresizingMaskIntoConstraints = false; content.addSubview(view) }
            NSLayoutConstraint.activate([
                status.topAnchor.constraint(equalTo:content.topAnchor,constant:16),status.leadingAnchor.constraint(equalTo:content.leadingAnchor,constant:16),status.trailingAnchor.constraint(equalTo:content.trailingAnchor,constant:-16),
                note.topAnchor.constraint(equalTo:status.bottomAnchor,constant:10),note.leadingAnchor.constraint(equalTo:status.leadingAnchor),note.trailingAnchor.constraint(equalTo:status.trailingAnchor),
                scroll.topAnchor.constraint(equalTo:note.bottomAnchor,constant:14),scroll.leadingAnchor.constraint(equalTo:status.leadingAnchor),scroll.trailingAnchor.constraint(equalTo:status.trailingAnchor),scroll.bottomAnchor.constraint(equalTo:content.bottomAnchor,constant:-16)
            ])
            panel.center(); window = panel
            timer = Timer.scheduledTimer(withTimeInterval:1,repeats:true) { [weak self] _ in self?.refresh() }
        }
        refresh(); window?.makeKeyAndOrderFront(nil)
    }
    func setStatus(_ message: String) { status.stringValue = message }
    func refresh() {
        guard window?.isVisible == true else { return }
        let folder = AppPaths.data.appendingPathComponent("logs")
        let files = (try? FileManager.default.contentsOfDirectory(at:folder,includingPropertiesForKeys:nil)) ?? []
        guard let latest = files.filter({ $0.lastPathComponent.hasPrefix("stock-runner-") }).sorted(by:{ $0.lastPathComponent < $1.lastPathComponent }).last,
              let file = try? FileHandle(forReadingFrom:latest) else {
            text.string = "Waiting for startup messages…"; return
        }
        defer { try? file.close() }
        let end = (try? file.seekToEnd()) ?? 0
        try? file.seek(toOffset:end > 32768 ? end-32768 : 0)
        let data = (try? file.readToEnd()) ?? Data()
        let value = "Runtime output · " + latest.lastPathComponent + "\n\n" + String(decoding:data,as:UTF8.self)
        if value != lastText { lastText = value; text.string = value; text.scrollToEndOfDocument(nil) }
    }
}

final class RelayDelegate: NSObject, NSApplicationDelegate {
    let session = URLSession(configuration:.ephemeral)
    var windows: [String:RelayWindowController] = [:]
    var dismissed = Set<String>()
    var missing: [String:Int] = [:]
    var pollTimer: Timer?
    var polling = false
    var stopping = false
    var waitingWindow: NSWindow?
    var waitingText: NSTextField?
    var launchTask: Process?
    var finishSetup = CommandLine.arguments.contains("--finish-setup")
    var frameHelper: Process?
    var lastFrameHelper = Date.distantPast
    var launchStarted = Date.distantPast
    var launcherValidated = !AppPaths.packaged || attachOnly
    let runtimeConsole = RuntimeConsole()

    func applicationDidFinishLaunching(_ notification: Notification) {
        let menu = NSMenu()
        let appItem = NSMenuItem()
        menu.addItem(appItem)
        let appMenu = NSMenu()
        appMenu.addItem(NSMenuItem(title:"Show Launcher Windows",action:#selector(showAllWindows),keyEquivalent:""))
        appMenu.addItem(NSMenuItem(title:"Show Runtime Log",action:#selector(showRuntimeLog),keyEquivalent:"l"))
        appMenu.addItem(.separator())
        appMenu.addItem(NSMenuItem(title:"Quit Launcher Relay",action:#selector(NSApplication.terminate(_:)),keyEquivalent:"q"))
        menu.setSubmenu(appMenu,for:appItem); NSApp.mainMenu = menu
        runtimeConsole.show()
        showWaiting("Connecting to launcher…")
        pollTimer = Timer.scheduledTimer(withTimeInterval:1,repeats:true) { [weak self] _ in self?.poll() }
        poll()
        if AppPaths.packaged && !attachOnly { startLauncher() }
    }
    @objc func showRuntimeLog() { runtimeConsole.show(); NSApp.activate(ignoringOtherApps:true) }
    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool {
        showRuntimeLog(); return true
    }
    @objc func showAllWindows() { dismissed.removeAll(); poll(); for controller in windows.values { controller.window.makeKeyAndOrderFront(nil) } }
    @objc func startLauncher() {
        guard launchTask == nil else { return }
        let root = AppPaths.scripts
        let task = Process()
        task.executableURL = AppPaths.python
        task.arguments = [root.appendingPathComponent("run_stock_launcher.py").path,"--display","relay","--debug","--switch-file",root.appendingPathComponent("cef-switches.txt").path]
        if finishSetup { task.arguments?.append("--finish-setup"); finishSetup = false }
        task.environment = AppPaths.environment
        task.currentDirectoryURL = AppPaths.data
        task.standardOutput = FileHandle.nullDevice; task.standardError = FileHandle.nullDevice
        task.terminationHandler = { [weak self] process in DispatchQueue.main.async {
            self?.launchTask = nil
            if process.terminationStatus != 0 { self?.showWaiting("Could not start launcher. Reopen the app to retry.") }
            else { self?.launcherValidated = true; self?.poll() }
        } }
        launchTask = task
        do { try task.run(); launchStarted = Date(); showWaiting("Starting official launcher…") }
        catch { launchTask = nil; showWaiting("Could not start launcher.") }
    }
    @objc func openLauncherLog() {
        let folder = AppPaths.data.appendingPathComponent("logs")
        let files = (try? FileManager.default.contentsOfDirectory(at:folder,includingPropertiesForKeys:nil)) ?? []
        if let latest = files.filter({ $0.lastPathComponent.hasPrefix("stock-runner-") }).sorted(by:{ $0.lastPathComponent < $1.lastPathComponent }).last {
            NSWorkspace.shared.open(latest)
        }
    }
    func showWaiting(_ text: String) {
        if waitingWindow == nil {
            let window = NSWindow(contentRect:NSRect(x:0,y:0,width:540,height:230),styleMask:[.titled,.closable,.miniaturizable,.resizable],backing:.buffered,defer:false)
            window.title = "Launcher — Connection"; window.isReleasedWhenClosed = false
            let label = NSTextField(wrappingLabelWithString:text)
            label.translatesAutoresizingMaskIntoConstraints = false
            let note = NSTextField(wrappingLabelWithString:"Startup details are available in Runtime Log. The official launcher page opens here when ready.")
            note.font = .systemFont(ofSize:12); note.textColor = .secondaryLabelColor; note.translatesAutoresizingMaskIntoConstraints = false
            let start = NSButton(title:"Start Launcher",target:self,action:#selector(startLauncher))
            let retry = NSButton(title:"Retry",target:self,action:#selector(showAllWindows))
            let log = NSButton(title:"Open Log",target:self,action:#selector(openLauncherLog))
            let buttons = NSStackView(views:[start,retry,log]); buttons.spacing = 12; buttons.translatesAutoresizingMaskIntoConstraints = false
            let content = window.contentView!
            content.addSubview(label); content.addSubview(note); content.addSubview(buttons)
            NSLayoutConstraint.activate([label.leadingAnchor.constraint(equalTo:content.leadingAnchor,constant:20),label.trailingAnchor.constraint(equalTo:content.trailingAnchor,constant:-20),label.topAnchor.constraint(equalTo:content.topAnchor,constant:20),note.leadingAnchor.constraint(equalTo:label.leadingAnchor),note.trailingAnchor.constraint(equalTo:label.trailingAnchor),note.topAnchor.constraint(equalTo:label.bottomAnchor,constant:16),buttons.leadingAnchor.constraint(equalTo:label.leadingAnchor),buttons.topAnchor.constraint(equalTo:note.bottomAnchor,constant:20)])
            waitingWindow = window; waitingText = label; window.center()
        }
        waitingText?.stringValue = text
        if windows.isEmpty { waitingWindow?.makeKeyAndOrderFront(nil); NSApp.activate(ignoringOtherApps:true) }
    }
    func poll() {
        guard launcherValidated, !polling, !stopping else { return }; polling = true
        if AppPaths.packaged, !attachOnly, Date().timeIntervalSince(lastFrameHelper) > 5, frameHelper?.isRunning != true {
            lastFrameHelper = Date()
            let helper = Process(); helper.executableURL = AppPaths.python
            helper.arguments = [AppPaths.scripts.appendingPathComponent("launcher_window.py").path,windows.isEmpty ? "--frame" : "--hide"]
            helper.environment = AppPaths.environment; helper.currentDirectoryURL = AppPaths.data
            helper.standardOutput = FileHandle.nullDevice; helper.standardError = FileHandle.nullDevice
            frameHelper = helper; try? helper.run()
        }
        session.dataTask(with:URL(string:"http://127.0.0.1:8088/json/list")!) { [weak self] data, _, error in
            DispatchQueue.main.async {
                guard let self = self, !self.stopping else { return }; self.polling = false
                guard error == nil, let data = data, let targets = try? JSONSerialization.jsonObject(with:data) as? [[String:Any]] else {
                    for controller in self.windows.values { controller.status.stringValue = "Launcher disconnected." }
                    self.runtimeConsole.setStatus("Waiting for the official launcher. Startup messages appear below.")
                    self.showWaiting(Date().timeIntervalSince(self.launchStarted) < 45 ? "Starting official launcher…" : "Launcher did not connect. Open Log for details, or click Start Launcher to retry.")
                    return
                }
                let allIDs = Set(targets.compactMap { $0["id"] as? String })
                self.dismissed.formIntersection(allIDs)
                for (ident, controller) in Array(self.windows) {
                    if !allIDs.contains(ident) {
                        self.missing[ident,default:0] += 1
                        if self.missing[ident,default:0] >= 2 { controller.window.close(); self.missing.removeValue(forKey:ident) }
                    } else { self.missing.removeValue(forKey:ident) }
                }
                let official = targets.filter { ($0["type"] as? String) == "page" && URL(string:$0["url"] as? String ?? "")?.host == "launcher.eu.4game.com" }
                let ordered = official.sorted {
                    let a = URL(string:$0["url"] as? String ?? "")?.path.hasPrefix("/window/") ?? false
                    let b = URL(string:$1["url"] as? String ?? "")?.path.hasPrefix("/window/") ?? false
                    return !a && b
                }
                if !ordered.isEmpty { self.waitingWindow?.orderOut(nil); self.runtimeConsole.setStatus("Connected. The original blank window is hidden; the runtime is still running.") }
                for target in ordered {
                    guard let ident = target["id"] as? String, self.windows[ident] == nil, !self.dismissed.contains(ident) else { continue }
                    let controller = RelayWindowController(target:target) { [weak self] closed in
                        self?.dismissed.insert(closed); self?.windows.removeValue(forKey:closed)
                    }
                    self.windows[ident] = controller
                }
            }
        }.resume()
    }
    func applicationWillTerminate(_ notification: Notification) { stopping = true; pollTimer?.invalidate(); for controller in windows.values { controller.shutdownTransport() }; session.invalidateAndCancel() }
    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { true }
}

// Direct mode hands the UI to the official Wine window. It never creates a
// RelayWindowController, captures screenshots, or runs the relay's hide timer.
final class DirectLauncherDelegate: NSObject, NSApplicationDelegate {
    var launchTask: Process?
    var errorFile: FileHandle?
    var errorURL: URL?

    func applicationDidFinishLaunching(_ notification: Notification) {
        let task = Process()
        task.executableURL = AppPaths.python
        task.arguments = [AppPaths.scripts.appendingPathComponent("run_stock_launcher.py").path, "--display", "direct"]
        if CommandLine.arguments.contains("--finish-setup") { task.arguments?.append("--finish-setup") }
        task.environment = AppPaths.environment
        task.currentDirectoryURL = AppPaths.data
        task.standardOutput = FileHandle.nullDevice
        let logs = AppPaths.data.appendingPathComponent("logs")
        do {
            try FileManager.default.createDirectory(at: logs, withIntermediateDirectories: true,
                                                    attributes: [.posixPermissions: 0o700])
            let url = logs.appendingPathComponent("direct-start-\(UUID().uuidString).log")
            guard FileManager.default.createFile(atPath: url.path, contents: nil,
                                                 attributes: [.posixPermissions: 0o600]) else {
                throw CocoaError(.fileWriteUnknown)
            }
            errorURL = url
            errorFile = try FileHandle(forWritingTo: url)
            task.standardError = errorFile
            task.terminationHandler = { [weak self] process in
                DispatchQueue.main.async {
                    guard let self = self else { return }
                    try? self.errorFile?.close()
                    self.errorFile = nil
                    if process.terminationStatus != 0 {
                        let detail = self.errorURL.flatMap { try? String(contentsOf: $0, encoding: .utf8) } ?? ""
                        self.showError(detail.isEmpty ? "Open the logs folder for startup details." : String(detail.suffix(4000)))
                    }
                    // The Wine window and game have their own processes and stay open.
                    NSApp.terminate(nil)
                }
            }
            launchTask = task
            try task.run()
            NSApp.setActivationPolicy(.accessory)
        } catch {
            try? errorFile?.close()
            showError(error.localizedDescription)
            NSApp.terminate(nil)
        }
    }
    func showError(_ detail: String) {
        NSApp.setActivationPolicy(.regular)
        NSApp.activate(ignoringOtherApps: true)
        let alert = NSAlert()
        alert.messageText = "Could not open Lineage II Launcher"
        alert.informativeText = detail
        alert.addButton(withTitle: "OK")
        alert.runModal()
    }
}

let attachOnly = CommandLine.arguments.contains("--attach-only")
let app = NSApplication.shared
let needsSetup = CommandLine.arguments.contains("--setup") || !FileManager.default.fileExists(atPath:AppPaths.config.path)
let useRelay = attachOnly || CommandLine.arguments.contains("--relay")
let delegate: NSApplicationDelegate = needsSetup ? SetupDelegate() : useRelay ? RelayDelegate() : DirectLauncherDelegate()
app.setActivationPolicy(.regular); app.delegate = delegate; app.run()
