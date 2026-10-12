import UIKit
import UniformTypeIdentifiers

enum ClipboardScreenshot {
    /// Only call in response to an explicit screenshot-paste action. Never polls the clipboard.
    @MainActor static func read() throws -> Data {
        let pasteboard = UIPasteboard.general
        for type in pasteboard.types where UTType(type)?.conforms(to: .image) == true {
            guard let data = pasteboard.data(forPasteboardType: type), !data.isEmpty else { continue }
            guard data.count <= 20_000_000 else { throw GoutouError.invalid("截图超过 20 MB，请先裁小聊天范围") }
            return data
        }
        throw GoutouError.invalid("剪贴板里没有图片。请在照片中打开聊天截图，点分享 → 拷贝照片，再返回读取；也可在狗头军师 App 里选择截图。")
    }
}
