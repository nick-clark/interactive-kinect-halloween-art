#!/usr/bin/env swift

import Foundation
import AppKit

// MARK: - Kinect Manager
class KinectManager: ObservableObject {
    @Published var isKinectConnected = false
    @Published var ledStatus: KinectLEDStatus = .unknown
    
    enum KinectLEDStatus {
        case off, green, red, blinking, unknown
        
        var color: NSColor {
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
    
    func checkKinectStatus() {
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
    
    func testKinect() {
        runPythonScript("test_kinect.py")
    }
    
    func resetKinect() {
        runShellScript("./kinect_reset.sh")
    }
    
    private func runPythonScript(_ scriptPath: String) {
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
    
    private func runShellScript(_ scriptPath: String) {
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

// MARK: - Process Manager
class ProcessManager: ObservableObject {
    @Published var pythonProcesses: [ProcessInfo] = []
    
    struct ProcessInfo {
        let pid: Int32
        let command: String
        let startTime: Date
    }
    
    func updateProcessList() {
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
            
            let processes = parseProcessOutput(output)
            
            DispatchQueue.main.async {
                self.pythonProcesses = processes
            }
        } catch {
            print("Failed to get process list: \(error)")
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
    
    func startScript(_ script: PythonScript) {
        let task = Process()
        task.launchPath = "/usr/bin/python3"
        task.arguments = [script.path]
        task.currentDirectoryPath = FileManager.default.currentDirectoryPath
        
        let pipe = Pipe()
        task.standardOutput = pipe
        task.standardError = pipe
        
        pipe.fileHandleForReading.readabilityHandler = { handle in
            let data = handle.availableData
            if !data.isEmpty {
                let output = String(data: data, encoding: .utf8) ?? ""
                DispatchQueue.main.async {
                    self.addLog(scriptName: script.name, message: output.trimmingCharacters(in: .newlines))
                }
            }
        }
        
        do {
            try task.run()
            
            if let index = scripts.firstIndex(where: { $0.name == script.name }) {
                scripts[index].isRunning = true
                scripts[index].process = task
            }
            
            addLog(scriptName: script.name, message: "Script started")
            
            DispatchQueue.global().async {
                task.waitUntilExit()
                DispatchQueue.main.async {
                    if let index = self.scripts.firstIndex(where: { $0.name == script.name }) {
                        self.scripts[index].isRunning = false
                        self.scripts[index].process = nil
                    }
                    self.addLog(scriptName: script.name, message: "Script terminated")
                }
            }
        } catch {
            addLog(scriptName: script.name, message: "Failed to start script: \(error)")
        }
    }
    
    func stopScript(_ script: PythonScript) {
        if let process = script.process {
            process.terminate()
            addLog(scriptName: script.name, message: "Script stopped by user")
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

// MARK: - Simple Console Interface
class KinectMasterConsole {
    private let kinectManager = KinectManager()
    private let processManager = ProcessManager()
    private let scriptManager = ScriptManager()
    private var running = true
    
    func run() {
        print("🎮 KinectMaster Console Interface")
        print("================================")
        
        kinectManager.checkKinectStatus()
        processManager.updateProcessList()
        scriptManager.discoverScripts()
        
        while running {
            displayMenu()
            handleInput()
        }
    }
    
    private func displayMenu() {
        print("\n📊 System Status:")
        print("  USB Device: \(kinectManager.isKinectConnected ? "✅ Kinect Connected" : "❌ Kinect Not Found")")
        print("  LED Status: \(kinectManager.ledStatus.description)")
        print("  Python Processes: \(processManager.pythonProcesses.count)")
        
        print("\n🎭 Available Scripts:")
        if scriptManager.scripts.isEmpty {
            print("  No Python scripts found")
        } else {
            for (index, script) in scriptManager.scripts.enumerated() {
                let status = script.isRunning ? "🟢 Running" : "⚪ Stopped"
                print("  \(index + 1). \(script.name) - \(status)")
            }
        }
        
        print("\n🔧 Commands:")
        print("  k - Kill all Python processes")
        print("  t - Test Kinect")
        print("  r - Reset Kinect")
        print("  s <number> - Start script by number")
        print("  q <number> - Quit script by number")
        print("  l - Show recent logs")
        print("  c - Clear logs")
        print("  u - Update status")
        print("  x - Exit")
        print("\nEnter command: ", terminator: "")
    }
    
    private func handleInput() {
        guard let input = readLine() else { return }
        let parts = input.trimmingCharacters(in: .whitespaces).components(separatedBy: " ")
        let command = parts[0].lowercased()
        
        switch command {
        case "k":
            print("🔪 Killing all Python processes...")
            processManager.killAllPythonProcesses()
            
        case "t":
            print("🧪 Testing Kinect...")
            kinectManager.testKinect()
            
        case "r":
            print("🔄 Resetting Kinect...")
            kinectManager.resetKinect()
            
        case "s":
            if let scriptIndex = Int(parts[1]), scriptIndex > 0, scriptIndex <= scriptManager.scripts.count {
                let script = scriptManager.scripts[scriptIndex - 1]
                print("🚀 Starting \(script.name)...")
                scriptManager.startScript(script)
            } else {
                print("❌ Invalid script number")
            }
            
        case "q":
            if let scriptIndex = Int(parts[1]), scriptIndex > 0, scriptIndex <= scriptManager.scripts.count {
                let script = scriptManager.scripts[scriptIndex - 1]
                print("🛑 Stopping \(script.name)...")
                scriptManager.stopScript(script)
            } else {
                print("❌ Invalid script number")
            }
            
        case "l":
            print("\n📋 Recent Logs:")
            let recentLogs = scriptManager.logs.suffix(10)
            for log in recentLogs {
                print("  [\(log.timestamp)] \(log.scriptName): \(log.message)")
            }
            
        case "c":
            print("🧹 Clearing logs...")
            scriptManager.clearLogs()
            
        case "u":
            print("🔄 Updating status...")
            kinectManager.checkKinectStatus()
            processManager.updateProcessList()
            scriptManager.discoverScripts()
            
        case "x":
            print("👋 Goodbye!")
            running = false
            
        default:
            print("❌ Unknown command: \(command)")
        }
    }
}

// MARK: - Main
let console = KinectMasterConsole()
console.run()

