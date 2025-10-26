#!/usr/bin/env swift

import Cocoa
import Foundation

// MARK: - Main App Delegate
class AppDelegate: NSObject, NSApplicationDelegate {
    var window: NSWindow!
    var kinectManager: KinectManager!
    var processManager: ProcessManager!
    var scriptManager: ScriptManager!
    
    func applicationDidFinishLaunching(_ notification: Notification) {
        // Initialize managers
        kinectManager = KinectManager()
        processManager = ProcessManager()
        scriptManager = ScriptManager()
        
        // Create main window
        createMainWindow()
        
        // Start monitoring
        kinectManager.startMonitoring()
        processManager.startMonitoring()
        scriptManager.discoverScripts()
    }
    
    func createMainWindow() {
        let windowRect = NSRect(x: 100, y: 100, width: 1000, height: 700)
        window = NSWindow(
            contentRect: windowRect,
            styleMask: [.titled, .closable, .miniaturizable, .resizable],
            backing: .buffered,
            defer: false
        )
        
        window.title = "KinectMaster Control Panel"
        window.center()
        
        // Create main view
        let mainView = MainView(
            kinectManager: kinectManager,
            processManager: processManager,
            scriptManager: scriptManager
        )
        
        window.contentView = NSHostingView(rootView: mainView)
        window.makeKeyAndOrderFront(nil)
    }
    
    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
        return true
    }
}

// MARK: - Kinect Manager
class KinectManager: ObservableObject {
    @Published var isKinectConnected = false
    @Published var ledStatus: KinectLEDStatus = .unknown
    
    enum KinectLEDStatus {
        case off, green, red, blinking, unknown
        
        var color: Color {
            switch self {
            case .off: return .gray
            case .green: return .green
            case .red: return .red
            case .blinking: return .orange
            case .unknown: return .gray
            }
        }
        
        var description: String {
            switch self {
            case .off: return "Off"
            case .green: return "Green"
            case .red: return "Red"
            case .blinking: return "Blinking"
            case .unknown: return "Unknown"
            }
        }
    }
    
    private var monitoringTimer: Timer?
    
    func startMonitoring() {
        monitoringTimer = Timer.scheduledTimer(withTimeInterval: 2.0, repeats: true) { _ in
            self.checkKinectStatus()
        }
        checkKinectStatus()
    }
    
    func stopMonitoring() {
        monitoringTimer?.invalidate()
        monitoringTimer = nil
    }
    
    private func checkKinectStatus() {
        DispatchQueue.global(qos: .background).async {
            let task = Process()
            task.launchPath = "/usr/sbin/system_profiler"
            task.arguments = ["SPUSBDataType"]
            
            let pipe = Pipe()
            task.standardOutput = pipe
            
            do {
                try task.run()
                task.waitUntilExit()
                
                let data = pipe.fileHandleForReading.readDataToEndOfFile()
                let output = String(data: data, encoding: .utf8) ?? ""
                
                DispatchQueue.main.async {
                    self.isKinectConnected = output.contains("Kinect")
                    self.ledStatus = self.isKinectConnected ? .green : .off
                }
            } catch {
                DispatchQueue.main.async {
                    self.isKinectConnected = false
                    self.ledStatus = .unknown
                }
            }
        }
    }
    
    func testKinect() {
        runPythonScript("test_kinect.py")
    }
    
    func resetKinect() {
        runShellScript("./kinect_reset.sh")
    }
    
    private func runPythonScript(_ scriptPath: String) {
        DispatchQueue.global(qos: .background).async {
            let task = Process()
            task.launchPath = "/usr/bin/python3"
            task.arguments = [scriptPath]
            task.currentDirectoryPath = FileManager.default.currentDirectoryPath
            
            do {
                try task.run()
            } catch {
                print("Failed to run Python script: \(error)")
            }
        }
    }
    
    private func runShellScript(_ scriptPath: String) {
        DispatchQueue.global(qos: .background).async {
            let task = Process()
            task.launchPath = "/bin/bash"
            task.arguments = [scriptPath]
            task.currentDirectoryPath = FileManager.default.currentDirectoryPath
            
            do {
                try task.run()
            } catch {
                print("Failed to run shell script: \(error)")
            }
        }
    }
}

// MARK: - Process Manager
class ProcessManager: ObservableObject {
    @Published var pythonProcesses: [ProcessInfo] = []
    
    struct ProcessInfo {
        let pid: Int32
        let command: String
        let startTime: Date
    }
    
    private var monitoringTimer: Timer?
    
    func startMonitoring() {
        monitoringTimer = Timer.scheduledTimer(withTimeInterval: 1.0, repeats: true) { _ in
            self.updateProcessList()
        }
        updateProcessList()
    }
    
    func stopMonitoring() {
        monitoringTimer?.invalidate()
        monitoringTimer = nil
    }
    
    private func updateProcessList() {
        DispatchQueue.global(qos: .background).async {
            let task = Process()
            task.launchPath = "/bin/ps"
            task.arguments = ["-axo", "pid,command"]
            
            let pipe = Pipe()
            task.standardOutput = pipe
            
            do {
                try task.run()
                task.waitUntilExit()
                
                let data = pipe.fileHandleForReading.readDataToEndOfFile()
                let output = String(data: data, encoding: .utf8) ?? ""
                
                let processes = self.parseProcessOutput(output)
                
                DispatchQueue.main.async {
                    self.pythonProcesses = processes
                }
            } catch {
                print("Failed to get process list: \(error)")
            }
        }
    }
    
    private func parseProcessOutput(_ output: String) -> [ProcessInfo] {
        var processes: [ProcessInfo] = []
        let lines = output.components(separatedBy: .newlines)
        
        for line in lines {
            if line.contains("python") && !line.contains("KinectMaster") {
                let components = line.trimmingCharacters(in: .whitespaces).components(separatedBy: .whitespaces)
                if components.count >= 2, let pid = Int32(components[0]) {
                    let command = components.dropFirst().joined(separator: " ")
                    processes.append(ProcessInfo(pid: pid, command: command, startTime: Date()))
                }
            }
        }
        
        return processes
    }
    
    func killAllPythonProcesses() {
        let killCommands = [
            "sudo pkill -9 -f python",
            "pkill -9 -f python", 
            "killall -9 Python",
            "killall -9 python3"
        ]
        
        for command in killCommands {
            runCommand(command)
        }
        
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) {
            self.updateProcessList()
        }
    }
    
    func killProcess(pid: Int32) {
        let command = "kill -9 \(pid)"
        runCommand(command)
        
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
            self.updateProcessList()
        }
    }
    
    private func runCommand(_ command: String) {
        DispatchQueue.global(qos: .background).async {
            let task = Process()
            task.launchPath = "/bin/bash"
            task.arguments = ["-c", command]
            
            do {
                try task.run()
            } catch {
                print("Failed to run command: \(command), error: \(error)")
            }
        }
    }
}

// MARK: - Script Manager
class ScriptManager: ObservableObject {
    @Published var scripts: [PythonScript] = []
    @Published var logs: [LogEntry] = []
    
    struct PythonScript {
        let name: String
        let path: String
        var isRunning: Bool = false
        var process: Process?
    }
    
    struct LogEntry: Identifiable {
        let id = UUID()
        let timestamp: String
        let scriptName: String
        let message: String
    }
    
    func discoverScripts() {
        DispatchQueue.global(qos: .background).async {
            let fileManager = FileManager.default
            let currentPath = fileManager.currentDirectoryPath
            
            do {
                let contents = try fileManager.contentsOfDirectory(atPath: currentPath)
                let pythonFiles = contents.filter { $0.hasSuffix(".py") && !$0.contains("test_") }
                
                DispatchQueue.main.async {
                    self.scripts = pythonFiles.map { fileName in
                        PythonScript(name: fileName, path: fileName)
                    }
                }
            } catch {
                print("Failed to discover scripts: \(error)")
            }
        }
    }
    
    func startScript(_ script: PythonScript) {
        // Open a new Terminal window for this script
        openTerminalForScript(script)
        
        // Update script status
        if let index = scripts.firstIndex(where: { $0.name == script.name }) {
            scripts[index].isRunning = true
            scripts[index].process = nil // We're not tracking the process directly
        }
        
        addLog(scriptName: script.name, message: "Script started in new Terminal window")
    }
    
    private func openTerminalForScript(_ script: PythonScript) {
        DispatchQueue.global(qos: .background).async {
            let command = "cd '\(FileManager.default.currentDirectoryPath)' && python3 '\(script.path)'"
            
            // Create AppleScript to open new Terminal window
            let appleScript = """
            tell application "Terminal"
                activate
                do script "\(command)"
            end tell
            """
            
            let task = Process()
            task.launchPath = "/usr/bin/osascript"
            task.arguments = ["-e", appleScript]
            
            do {
                try task.run()
            } catch {
                print("Failed to open Terminal: \(error)")
                DispatchQueue.main.async {
                    self.addLog(scriptName: script.name, message: "Failed to open Terminal window: \(error)")
                }
            }
        }
    }
    
    func stopScript(_ script: PythonScript) {
        // Just kill all Python processes - much simpler and more reliable
        killAllPythonProcesses()
        
        // Update script status
        if let index = scripts.firstIndex(where: { $0.name == script.name }) {
            scripts[index].isRunning = false
            scripts[index].process = nil
        }
        
        addLog(scriptName: script.name, message: "All Python processes killed")
    }
    
    private func killAllPythonProcesses() {
        let killCommands = [
            "sudo pkill -9 -f python",
            "pkill -9 -f python", 
            "killall -9 Python",
            "killall -9 python3"
        ]
        
        for command in killCommands {
            runCommand(command)
        }
    }
    
    private func runCommand(_ command: String) {
        DispatchQueue.global(qos: .background).async {
            let task = Process()
            task.launchPath = "/bin/bash"
            task.arguments = ["-c", command]
            
            do {
                try task.run()
            } catch {
                print("Failed to run command: \(command), error: \(error)")
            }
        }
    }
    
    func clearLogs() {
        logs.removeAll()
    }
    
    private func addLog(scriptName: String, message: String) {
        let formatter = DateFormatter()
        formatter.dateFormat = "HH:mm:ss"
        let timestamp = formatter.string(from: Date())
        
        let logEntry = LogEntry(timestamp: timestamp, scriptName: scriptName, message: message)
        logs.append(logEntry)
        
        if logs.count > 1000 {
            logs.removeFirst(logs.count - 1000)
        }
    }
}

// MARK: - SwiftUI Views
import SwiftUI

struct MainView: View {
    @ObservedObject var kinectManager: KinectManager
    @ObservedObject var processManager: ProcessManager
    @ObservedObject var scriptManager: ScriptManager
    
    var body: some View {
        VStack(spacing: 0) {
            // Header
            HStack {
                Image(systemName: "camera.viewfinder")
                    .font(.title)
                    .foregroundColor(.blue)
                Text("KinectMaster Control Panel")
                    .font(.title2)
                    .fontWeight(.bold)
                Spacer()
            }
            .padding()
            .background(Color(NSColor.windowBackgroundColor))
            
            // Main Content - 2 Column Layout
            HStack(spacing: 0) {
                // Left Column - Controls and Status
                ScrollView {
                    VStack(spacing: 20) {
                        // System Status Section
                        SystemStatusSection(kinectManager: kinectManager, processManager: processManager)
                        
                        // Process Management Section
                        ProcessManagementSection(processManager: processManager)
                        
                        // Kinect Controls Section
                        KinectControlsSection(kinectManager: kinectManager)
                        
                        // Experiences Section
                        ExperiencesSection(scriptManager: scriptManager)
                    }
                    .padding()
                }
                .frame(width: 400)
                .background(Color(NSColor.controlBackgroundColor))
                
                // Divider
                Rectangle()
                    .fill(Color(NSColor.separatorColor))
                    .frame(width: 1)
                
                // Right Column - Activity Log
                LogViewerSection(scriptManager: scriptManager)
                    .frame(maxWidth: .infinity)
            }
        }
        .frame(minWidth: 1000, minHeight: 700)
    }
}

struct SystemStatusSection: View {
    @ObservedObject var kinectManager: KinectManager
    @ObservedObject var processManager: ProcessManager
    
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Image(systemName: "info.circle")
                    .foregroundColor(.blue)
                Text("System Status")
                    .font(.headline)
                Spacer()
            }
            
            HStack(spacing: 20) {
                // USB Device Status
                VStack(alignment: .leading, spacing: 4) {
                    Text("USB Device")
                        .font(.subheadline)
                        .fontWeight(.medium)
                    HStack {
                        Circle()
                            .fill(kinectManager.isKinectConnected ? .green : .red)
                            .frame(width: 8, height: 8)
                        Text(kinectManager.isKinectConnected ? "Kinect Connected" : "Kinect Not Found")
                            .font(.caption)
                    }
                }
                
                // Kinect LED Status
                VStack(alignment: .leading, spacing: 4) {
                    Text("Kinect LED")
                        .font(.subheadline)
                        .fontWeight(.medium)
                    HStack {
                        Circle()
                            .fill(kinectManager.ledStatus.color)
                            .frame(width: 8, height: 8)
                        Text(kinectManager.ledStatus.description)
                            .font(.caption)
                    }
                }
                
                // Active Processes
                VStack(alignment: .leading, spacing: 4) {
                    Text("Active Processes")
                        .font(.subheadline)
                        .fontWeight(.medium)
                    Text("\(processManager.pythonProcesses.count) Python processes")
                        .font(.caption)
                }
                
                Spacer()
            }
        }
        .padding()
        .background(Color(NSColor.controlBackgroundColor))
        .cornerRadius(8)
    }
}

struct ProcessManagementSection: View {
    @ObservedObject var processManager: ProcessManager
    
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Image(systemName: "gearshape")
                    .foregroundColor(.orange)
                Text("Process Management")
                    .font(.headline)
                Spacer()
            }
            
            VStack(spacing: 8) {
                // Kill Python Button
                Button(action: {
                    processManager.killAllPythonProcesses()
                }) {
                    HStack {
                        Image(systemName: "trash")
                        Text("Kill All Python Processes")
                    }
                    .foregroundColor(.white)
                    .padding()
                    .background(Color.red)
                    .cornerRadius(8)
                }
                
                // Process List
                if !processManager.pythonProcesses.isEmpty {
                    VStack(alignment: .leading, spacing: 4) {
                        Text("Running Python Processes:")
                            .font(.subheadline)
                            .fontWeight(.medium)
                        
                        ForEach(processManager.pythonProcesses, id: \.pid) { process in
                            HStack {
                                Text("PID: \(process.pid)")
                                    .font(.caption)
                                    .foregroundColor(.secondary)
                                Text(process.command)
                                    .font(.caption)
                                Spacer()
                                Button("Kill") {
                                    processManager.killProcess(pid: process.pid)
                                }
                                .font(.caption)
                                .foregroundColor(.red)
                            }
                            .padding(.horizontal)
                        }
                    }
                } else {
                    Text("No Python processes running")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }
        }
        .padding()
        .background(Color(NSColor.controlBackgroundColor))
        .cornerRadius(8)
    }
}

struct KinectControlsSection: View {
    @ObservedObject var kinectManager: KinectManager
    
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Image(systemName: "camera")
                    .foregroundColor(.purple)
                Text("Kinect Controls")
                    .font(.headline)
                Spacer()
            }
            
            HStack(spacing: 12) {
                Button(action: {
                    kinectManager.testKinect()
                }) {
                    HStack {
                        Image(systemName: "play.circle")
                        Text("Test Kinect")
                    }
                    .foregroundColor(.white)
                    .padding()
                    .background(Color.blue)
                    .cornerRadius(8)
                }
                
                Button(action: {
                    kinectManager.resetKinect()
                }) {
                    HStack {
                        Image(systemName: "arrow.clockwise")
                        Text("Reset Kinect")
                    }
                    .foregroundColor(.white)
                    .padding()
                    .background(Color.orange)
                    .cornerRadius(8)
                }
            }
        }
        .padding()
        .background(Color(NSColor.controlBackgroundColor))
        .cornerRadius(8)
    }
}

struct ExperiencesSection: View {
    @ObservedObject var scriptManager: ScriptManager
    
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Image(systemName: "star")
                    .foregroundColor(.green)
                Text("Experiences")
                    .font(.headline)
                Spacer()
                Button("Refresh") {
                    scriptManager.discoverScripts()
                }
                .font(.caption)
            }
            
            if scriptManager.scripts.isEmpty {
                Text("No Python scripts found in current directory")
                    .font(.caption)
                    .foregroundColor(.secondary)
            } else {
                ForEach(scriptManager.scripts, id: \.name) { script in
                    ScriptRowView(script: script, scriptManager: scriptManager)
                }
            }
        }
        .padding()
        .background(Color(NSColor.controlBackgroundColor))
        .cornerRadius(8)
    }
}

struct ScriptRowView: View {
    let script: ScriptManager.PythonScript
    @ObservedObject var scriptManager: ScriptManager
    
    var body: some View {
        HStack {
            VStack(alignment: .leading, spacing: 4) {
                Text(script.name)
                    .font(.subheadline)
                    .fontWeight(.medium)
                Text(script.path)
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            
            Spacer()
            
            HStack(spacing: 8) {
                if script.isRunning {
                    Button("Quit") {
                        scriptManager.stopScript(script)
                    }
                    .foregroundColor(.white)
                    .padding(.horizontal, 12)
                    .padding(.vertical, 6)
                    .background(Color.red)
                    .cornerRadius(6)
                    
                    Circle()
                        .fill(Color.green)
                        .frame(width: 8, height: 8)
                } else {
                    Button("Launch") {
                        scriptManager.startScript(script)
                    }
                    .foregroundColor(.white)
                    .padding(.horizontal, 12)
                    .padding(.vertical, 6)
                    .background(Color.green)
                    .cornerRadius(6)
                    
                    Circle()
                        .fill(Color.gray)
                        .frame(width: 8, height: 8)
                }
            }
        }
        .padding(.vertical, 4)
    }
}

struct LogViewerSection: View {
    @ObservedObject var scriptManager: ScriptManager
    
    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            // Header
            HStack {
                Image(systemName: "doc.text")
                    .foregroundColor(.indigo)
                Text("Activity Log")
                    .font(.headline)
                Spacer()
                Button("Clear") {
                    scriptManager.clearLogs()
                }
                .font(.caption)
            }
            .padding()
            .background(Color(NSColor.windowBackgroundColor))
            
            // Info text
            Text("Scripts run in separate Terminal windows. Check the Terminal for detailed output.")
                .font(.caption)
                .foregroundColor(.secondary)
                .padding(.horizontal)
                .padding(.bottom, 8)
            
            // Log content - takes remaining space
            ScrollView {
                VStack(alignment: .leading, spacing: 2) {
                    ForEach(scriptManager.logs, id: \.id) { logEntry in
                        HStack {
                            Text(logEntry.timestamp)
                                .font(.caption)
                                .foregroundColor(.secondary)
                                .frame(width: 80, alignment: .leading)
                            
                            Text(logEntry.scriptName)
                                .font(.caption)
                                .foregroundColor(.blue)
                                .frame(width: 120, alignment: .leading)
                            
                            Text(logEntry.message)
                                .font(.caption)
                                .foregroundColor(.primary)
                            
                            Spacer()
                        }
                        .padding(.horizontal, 8)
                        .padding(.vertical, 2)
                    }
                }
                .padding(.horizontal)
            }
            .background(Color(NSColor.textBackgroundColor))
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}

// MARK: - Main
let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.run()
