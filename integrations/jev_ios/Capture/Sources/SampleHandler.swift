import ReplayKit
import CoreImage
import ImageIO
import UniformTypeIdentifiers

/// The system delivers frames only after the user confirms its broadcast sheet.
/// This extension has no network client. It recognizes locally or returns an
/// image for cloud upload confirmation in the keyboard, according to settings.
final class SampleHandler: RPBroadcastSampleHandler {
    private let lock = NSLock()
    private var active = false
    private var processing = false
    private var request: KeyboardCaptureRequest?
    private var store: GoutouStore?
    private var started = Date()
    private var job: Task<Void, Never>?
    private var deadline: DispatchWorkItem?

    override func broadcastStarted(withSetupInfo setupInfo: [String: NSObject]?) {
        do {
            let store = try GoutouStore()
            guard let request = store.captureMailbox.request(), request.relationship == store.relationship(),
                  request.config == store.config() else {
                throw GoutouError.invalid("请先在狗头军师键盘点击截屏，再确认系统捕获")
            }
            self.store = store; self.request = request; started = Date()
            lock.lock(); active = true; processing = false; lock.unlock()
            let timeout = DispatchWorkItem { [weak self] in self?.complete(text: "", error: "截屏超时；请回到聊天页面重试") }
            deadline = timeout
            DispatchQueue.global().asyncAfter(deadline: .now() + 15, execute: timeout)
        } catch { finishBroadcastWithError(error) }
    }

    override func processSampleBuffer(_ sampleBuffer: CMSampleBuffer, with sampleBufferType: RPSampleBufferType) {
        guard sampleBufferType == .video else { return } // Microphone/app audio is never processed.
        lock.lock()
        guard active, !processing, Date().timeIntervalSince(started) >= 0.6,
              let request = request else { lock.unlock(); return }
        processing = true; lock.unlock()
        do {
            let data = try frame(sampleBuffer, excludedBottomFraction: request.excludedBottomFraction)
            job = Task { [weak self] in
                do {
                    let result = try await CaptureOCR.prepare(data, request: request)
                    try Task.checkCancellation()
                    self?.complete(text: result.transcript, error: nil, screenshot: result.screenshot)
                } catch { self?.complete(text: "", error: error.localizedDescription) }
            }
        } catch { complete(text: "", error: error.localizedDescription) }
    }

    override func broadcastFinished() {
        lock.lock(); active = false; lock.unlock()
        deadline?.cancel(); job?.cancel(); job = nil
    }
    override func broadcastPaused() { complete(text: "", error: "系统屏幕捕获已暂停，请重试") }

    private func complete(text: String, error: String?, screenshot: Data? = nil) {
        lock.lock()
        guard active else { lock.unlock(); return }
        active = false; lock.unlock()
        deadline?.cancel(); job?.cancel()
        var message = error ?? (screenshot == nil ? "本次截屏识图已完成，请返回狗头军师键盘核对。"
            : "截图已交给键盘，请返回预览并确认云端识别。")
        do {
            guard let store = store, let request = request, store.relationship() == request.relationship,
                  store.config() == request.config else { throw GoutouError.invalid("对象或配置已变化，请重新截屏") }
            try store.captureMailbox.publish(KeyboardCaptureResult(request: request, transcript: text, error: error, screenshot: screenshot))
        } catch { message = error.localizedDescription }
        // ReplayKit exposes only this termination API to upload extensions. iOS may
        // present a “broadcast stopped” notice even when the single-frame job succeeds.
        finishBroadcastWithError(NSError(domain: "ai.goutoujunshi.capture", code: error == nil ? 1 : 2,
                                         userInfo: [NSLocalizedDescriptionKey: message]))
    }

    private func frame(_ sample: CMSampleBuffer, excludedBottomFraction: Double) throws -> Data {
        guard let buffer = CMSampleBufferGetImageBuffer(sample) else { throw GoutouError.invalid("系统未返回可用画面") }
        let context = CIContext(options: [.cacheIntermediates: false])
        var image = CIImage(cvPixelBuffer: buffer)
        if let orientation = CMGetAttachment(sample, key: RPVideoSampleOrientationKey as CFString,
                                              attachmentModeOut: nil) as? NSNumber {
            image = image.oriented(forExifOrientation: orientation.int32Value)
        }
        // Bound memory in the 50 MB broadcast process before creating a CGImage.
        let scale = min(1, 1600 / max(image.extent.width, image.extent.height))
        image = image.transformed(by: CGAffineTransform(scaleX: scale, y: scale))
        guard let full = context.createCGImage(image, from: image.extent),
              let cropped = full.cropping(to: CGRect(x: 0, y: 0, width: full.width,
                  height: max(1, Int(Double(full.height) * (1 - excludedBottomFraction))))) else {
            throw GoutouError.invalid("截屏转换失败，请重试")
        }
        let data = NSMutableData()
        guard let destination = CGImageDestinationCreateWithData(data, UTType.jpeg.identifier as CFString, 1, nil) else {
            throw GoutouError.invalid("截屏编码失败")
        }
        CGImageDestinationAddImage(destination, cropped, [kCGImageDestinationLossyCompressionQuality: 0.85] as CFDictionary)
        guard CGImageDestinationFinalize(destination) else { throw GoutouError.invalid("截屏编码失败") }
        return data as Data
    }
}
