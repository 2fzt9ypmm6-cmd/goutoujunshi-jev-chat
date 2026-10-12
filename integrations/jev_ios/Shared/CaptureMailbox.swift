import Foundation

/// User-armed capture handoff. Cloud OCR returns a bounded image for explicit
/// upload confirmation; local OCR returns text. No audio or credentials are stored.
struct KeyboardCaptureRequest: Codable, Equatable {
    var id = UUID()
    var relationship: Relationship
    var config: AppConfig
    var excludedBottomFraction: Double
    var createdAt = Date()

    func valid(at date: Date) -> Bool {
        (0...90).contains(date.timeIntervalSince(createdAt)) &&
        (0...0.7).contains(excludedBottomFraction)
    }
}

struct KeyboardCaptureResult: Codable {
    var request: KeyboardCaptureRequest
    var transcript: String
    var error: String?
    var screenshot: Data? = nil
    var createdAt = Date()

    func valid(at date: Date, relationship: Relationship, config: AppConfig) -> Bool {
        guard (0...300).contains(date.timeIntervalSince(createdAt)) &&
        self.request.relationship == relationship && self.request.config == config &&
        transcript.count <= 12_000 && (error?.count ?? 0) <= 500 else { return false }
        if let error = error { return !error.trimmed.isEmpty && transcript.isEmpty && screenshot == nil }
        if let screenshot = screenshot {
            return config.ocr != .local && transcript.isEmpty && screenshot.count <= 4_000_000 &&
                screenshot.prefix(3) == Data([0xff, 0xd8, 0xff])
        }
        return !transcript.trimmed.isEmpty
    }
}

final class CaptureMailbox {
    private let container: URL
    init(container: URL) { self.container = container }

    func arm(_ request: KeyboardCaptureRequest) throws {
        guard request.valid(at: Date()) else { throw GoutouError.invalid("截屏请求已过期，请重新点击截屏") }
        clear()
        try write(request, name: "capture-request.json")
    }
    func request() -> KeyboardCaptureRequest? {
        guard let value: KeyboardCaptureRequest = read("capture-request.json"), value.valid(at: Date()) else {
            // A completed result may remain usable for five minutes after the request expires.
            if !FileManager.default.fileExists(atPath: path("capture-result.json").path) { clear() }
            return nil
        }
        return value
    }
    func publish(_ result: KeyboardCaptureResult) throws {
        guard let active = request(), active == result.request,
              result.valid(at: Date(), relationship: active.relationship, config: active.config) else {
            throw GoutouError.invalid("截屏请求已取消或过期")
        }
        try write(result, name: "capture-result.json")
    }
    func take(relationship: Relationship, config: AppConfig) -> KeyboardCaptureResult? {
        let result = peek(relationship: relationship, config: config)
        if result != nil { clear() }
        return result
    }
    /// Images remain available while the keyboard waits for upload confirmation,
    /// including dismissal/recreation. Text is consumed by take().
    func peek(relationship: Relationship, config: AppConfig) -> KeyboardCaptureResult? {
        guard FileManager.default.fileExists(atPath: path("capture-result.json").path) else { return nil }
        guard let result: KeyboardCaptureResult = read("capture-result.json"),
              let active: KeyboardCaptureRequest = read("capture-request.json"), active == result.request,
              result.valid(at: Date(), relationship: relationship, config: config) else { clear(); return nil }
        return result
    }
    func purge(relationship: Relationship, config: AppConfig) {
        if FileManager.default.fileExists(atPath: path("capture-result.json").path) {
            guard let result: KeyboardCaptureResult = read("capture-result.json"),
                  let active: KeyboardCaptureRequest = read("capture-request.json"), active == result.request,
                  result.valid(at: Date(), relationship: relationship, config: config) else { clear(); return }
        } else if let active = request(), active.relationship != relationship || active.config != config { clear() }
    }
    func clear() {
        for name in ["capture-request.json", "capture-result.json"] { try? FileManager.default.removeItem(at: path(name)) }
    }
    private func path(_ name: String) -> URL { container.appendingPathComponent(name) }
    private func limit(_ name: String) -> Int { name == "capture-result.json" ? 5_500_000 : 100_000 }
    private func read<T: Decodable>(_ name: String) -> T? {
        guard let size = try? path(name).resourceValues(forKeys: [.fileSizeKey]).fileSize,
              size <= limit(name), let data = try? Data(contentsOf: path(name)) else { return nil }
        return try? JSONDecoder().decode(T.self, from: data)
    }
    private func write<T: Encodable>(_ value: T, name: String) throws {
        let data = try JSONEncoder().encode(value)
        guard data.count <= limit(name) else { throw GoutouError.invalid("截屏内容过大，请缩小聊天范围") }
        try FileManager.default.createDirectory(at: container, withIntermediateDirectories: true)
        #if os(iOS)
        try data.write(to: path(name), options: [.atomic, .completeFileProtectionUntilFirstUserAuthentication])
        do {
            var file = path(name), values = URLResourceValues()
            values.isExcludedFromBackup = true
            try file.setResourceValues(values)
        } catch { clear(); throw error }
        #else
        try data.write(to: path(name), options: .atomic)
        #endif
    }
}
