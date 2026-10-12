#if canImport(UIKit)
import UIKit

/// Shared by the app and its keyboard so their light and dark appearances stay consistent.
enum BrandTheme {
    private static func adaptive(_ light: UInt32, _ dark: UInt32) -> UIColor {
        UIColor { traits in
            let hex = traits.userInterfaceStyle == .dark ? dark : light
            return UIColor(red: CGFloat((hex >> 16) & 255) / 255,
                           green: CGFloat((hex >> 8) & 255) / 255,
                           blue: CGFloat(hex & 255) / 255, alpha: 1)
        }
    }

    static let background = adaptive(0xFFF8EF, 0x211A16)
    static let surface = adaptive(0xFFFDFA, 0x30251F)
    static let highlight = adaptive(0xFBE7D3, 0x493124)
    static let accent = adaptive(0xA95524, 0xF0AD78)
    static let primary = adaptive(0x70442D, 0xEDAD7B)
    static let onPrimary = adaptive(0xFFF9F0, 0x2B1D15)
    static let text = adaptive(0x483024, 0xF8EBDD)
    static let secondaryText = adaptive(0x7B675A, 0xC7AF9E)
    static let separator = adaptive(0xEAD9C8, 0x634A39)
    static let chartRise = adaptive(0xB66025, 0xEDA068)
    static let chartFall = adaptive(0x78635C, 0xB9A89E)
    static let chartEvent = adaptive(0x9C6E22, 0xEAC078)
}
#endif
