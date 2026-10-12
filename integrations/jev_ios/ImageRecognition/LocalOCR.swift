import Foundation
import Vision
import ImageIO
import UniformTypeIdentifiers

/// Capture processes never upload images. The configured cloud providers receive
/// a preview in the keyboard, then its explicit upload button invokes ModelAPI.
enum CaptureOCR {
    static func prepare(_ jpeg: Data, request: KeyboardCaptureRequest) async throws -> KeyboardCaptureResult {
        try Task.checkCancellation()
        if request.config.ocr == .local {
            let text = try await LocalOCR.recognize(jpeg, maxPixelSize: 1600)
            return KeyboardCaptureResult(request: request, transcript: text)
        }
        guard jpeg.count <= 4_000_000 else { throw GoutouError.invalid("截图过大，请重新截屏") }
        _ = try LocalOCR.image(jpeg, maxPixelSize: 480) // Decode only; no Vision recognition.
        return KeyboardCaptureResult(request: request, transcript: "", screenshot: jpeg)
    }
}

/// Shared by the app and keyboard. Decode a bounded thumbnail rather than a full-resolution photo.
enum LocalOCR {
    static func image(_ data: Data, maxPixelSize: Int = 2000) throws -> CGImage {
        guard !data.isEmpty, data.count <= 20_000_000,
              let source = CGImageSourceCreateWithData(data as CFData, [kCGImageSourceShouldCache: false] as CFDictionary),
              let image = CGImageSourceCreateThumbnailAtIndex(source, 0, [
                kCGImageSourceCreateThumbnailFromImageAlways: true,
                kCGImageSourceCreateThumbnailWithTransform: true,
                kCGImageSourceThumbnailMaxPixelSize: maxPixelSize,
                kCGImageSourceShouldCacheImmediately: true
              ] as CFDictionary) else {
            throw GoutouError.invalid("图片无法读取，请选择 20 MB 以内的聊天截图")
        }
        return image
    }
    static func boundedJPEG(_ data: Data, maxPixelSize: Int = 2000, excludedBottomFraction: Double = 0) throws -> Data {
        guard excludedBottomFraction.isFinite, (0...0.7).contains(excludedBottomFraction) else {
            throw GoutouError.invalid("截图裁剪范围无效，请重新准备识图")
        }
        let full = try image(data, maxPixelSize: maxPixelSize)
        guard let image = full.cropping(to: CGRect(x: 0, y: 0, width: full.width,
              height: max(1, Int(Double(full.height) * (1 - excludedBottomFraction))))) else {
            throw GoutouError.invalid("截图裁剪失败，请重新准备识图")
        }
        let output = NSMutableData()
        guard let destination = CGImageDestinationCreateWithData(output, UTType.jpeg.identifier as CFString, 1, nil) else {
            throw GoutouError.invalid("截图转换失败，请换一张图片")
        }
        // Re-encode visible pixels only; no source EXIF, location, or other metadata is copied.
        CGImageDestinationAddImage(destination, image, [kCGImageDestinationLossyCompressionQuality: 0.85] as CFDictionary)
        guard CGImageDestinationFinalize(destination), output.length <= 4_000_000 else {
            throw GoutouError.invalid("截图过大，请裁小聊天范围")
        }
        return output as Data
    }
    static func recognize(_ data: Data, maxPixelSize: Int = 2000) async throws -> String {
        let job = Task.detached(priority: .userInitiated) {
            try Task.checkCancellation()
            let cgImage = try Self.image(data, maxPixelSize: maxPixelSize)
            let request = VNRecognizeTextRequest()
            request.recognitionLevel = .accurate
            request.recognitionLanguages = ["zh-Hans", "en-US"]
            request.usesLanguageCorrection = true
            try VNImageRequestHandler(cgImage: cgImage, options: [:]).perform([request])
            try Task.checkCancellation()
            let observations = (request.results ?? []).sorted { $0.boundingBox.midY > $1.boundingBox.midY }
            let lines = observations.compactMap { observation -> String? in
                guard let text = observation.topCandidates(1).first?.string, !text.trimmed.isEmpty else { return nil }
                let x = observation.boundingBox.midX
                let speaker = x > 0.58 ? "我" : (x < 0.42 ? "对方" : "说话人待确认")
                return speaker + "：" + text
            }
            let text = lines.joined(separator: "\n")
            guard !text.isEmpty, text.count <= 12_000 else { throw GoutouError.invalid("未识别到文字，或内容过长；请缩小聊天范围") }
            return text
        }
        return try await withTaskCancellationHandler(operation: { try await job.value }, onCancel: { job.cancel() })
    }
}
