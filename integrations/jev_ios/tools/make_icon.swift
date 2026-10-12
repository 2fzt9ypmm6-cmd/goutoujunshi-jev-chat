import AppKit
import Foundation
import ImageIO

// Export all iPhone icon sizes from the approved opaque brand artwork.
guard CommandLine.arguments.count >= 2 else {
    fatalError("Usage: swift tools/make_icon.swift OUTPUT_DIRECTORY [SOURCE_IMAGE]")
}
let output = URL(fileURLWithPath: CommandLine.arguments[1], isDirectory: true)
let defaultSource = URL(fileURLWithPath: #filePath).deletingLastPathComponent()
    .deletingLastPathComponent().appendingPathComponent("Design/app-icon-master.png")
let sourceURL = CommandLine.arguments.count > 2
    ? URL(fileURLWithPath: CommandLine.arguments[2]) : defaultSource
guard let source = CGImageSourceCreateWithURL(sourceURL as CFURL, nil),
      let artwork = CGImageSourceCreateImageAtIndex(source, 0, nil),
      artwork.width == artwork.height else { fatalError("Icon artwork must be a readable square image") }
try FileManager.default.createDirectory(at: output, withIntermediateDirectories: true)
var entries = [[String: String]]()
let sizes: [(String, String, Int)] = [
    ("20x20", "2x", 40), ("20x20", "3x", 60), ("29x29", "2x", 58),
    ("29x29", "3x", 87), ("40x40", "2x", 80), ("40x40", "3x", 120),
    ("60x60", "2x", 120), ("60x60", "3x", 180), ("1024x1024", "1x", 1024)
]
for (size, scale, pixels) in sizes {
    guard let bitmap = CGContext(data: nil, width: pixels, height: pixels, bitsPerComponent: 8,
        bytesPerRow: pixels * 4, space: CGColorSpace(name: CGColorSpace.sRGB)!,
        bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue) else { fatalError("Cannot draw icon") }
    bitmap.setFillColor(CGColor(red: 0.96, green: 0.92, blue: 0.87, alpha: 1))
    let bounds = CGRect(x: 0, y: 0, width: pixels, height: pixels)
    bitmap.fill(bounds)
    bitmap.interpolationQuality = .high
    bitmap.draw(artwork, in: bounds)
    let filename = "icon-\(size)-\(scale).png"
    guard let image = bitmap.makeImage(), let destination = CGImageDestinationCreateWithURL(
        output.appendingPathComponent(filename) as CFURL, "public.png" as CFString, 1, nil) else { fatalError("Cannot save icon") }
    CGImageDestinationAddImage(destination, image, nil)
    guard CGImageDestinationFinalize(destination) else { fatalError("Cannot write icon") }
    entries.append(["size": size, "scale": scale, "idiom": pixels == 1024 ? "ios-marketing" : "iphone", "filename": filename])
}
let contents: [String: Any] = ["images": entries, "info": ["author": "goutoujunshi", "version": 1]]
try JSONSerialization.data(withJSONObject: contents, options: [.prettyPrinted, .sortedKeys]).write(to: output.appendingPathComponent("Contents.json"))
