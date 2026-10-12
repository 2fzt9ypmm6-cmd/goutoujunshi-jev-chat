// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "GoutouCore",
    platforms: [.macOS(.v13), .iOS(.v16)],
    products: [.library(name: "GoutouCore", targets: ["GoutouCore"])],
    targets: [
        .target(name: "GoutouCore", path: "Shared", exclude: ["BrandAssets.xcassets"])
    ]
)
