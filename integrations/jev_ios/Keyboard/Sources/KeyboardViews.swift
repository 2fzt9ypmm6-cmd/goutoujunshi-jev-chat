import UIKit

enum KB {
    static let primary = BrandTheme.primary
    static let onPrimary = BrandTheme.onPrimary
    static let ink = BrandTheme.text
    static let secondary = BrandTheme.secondaryText
    static let cream = BrandTheme.background
    static let surface = BrandTheme.surface
    static let highlight = BrandTheme.highlight
    static func label(_ text: String, size: CGFloat, bold: Bool = false) -> UILabel {
        let label = UILabel()
        label.text = text; label.numberOfLines = 0; label.textColor = ink
        label.font = UIFontMetrics.default.scaledFont(for: .systemFont(ofSize: size, weight: bold ? .semibold : .regular))
        label.adjustsFontForContentSizeCategory = true
        label.setContentCompressionResistancePriority(.required, for: .vertical)
        return label
    }
    static func button(_ title: String, icon: String? = nil, primary: Bool = false, action: (() -> Void)? = nil) -> UIButton {
        let button = UIButton(type: .system)
        var config = UIButton.Configuration.filled()
        config.title = title; config.cornerStyle = .capsule
        config.baseBackgroundColor = primary ? KB.primary : highlight
        config.baseForegroundColor = primary ? onPrimary : ink
        if let icon = icon { config.image = UIImage(systemName: icon); config.imagePadding = 5 }
        config.contentInsets = NSDirectionalEdgeInsets(top: 10, leading: 10, bottom: 10, trailing: 10)
        button.configuration = config
        button.titleLabel?.font = .preferredFont(forTextStyle: .subheadline)
        button.titleLabel?.numberOfLines = 2
        button.heightAnchor.constraint(greaterThanOrEqualToConstant: 44).isActive = true
        if let action = action { button.addAction(UIAction { _ in action() }, for: .touchUpInside) }
        return button
    }
    static func row(_ views: [UIView]) -> UIStackView {
        let stack = UIStackView(arrangedSubviews: views)
        stack.axis = .horizontal; stack.spacing = 8; stack.distribution = .fillEqually
        return stack
    }
    static func card(_ views: [UIView], highlighted: Bool = false) -> UIView {
        let stack = UIStackView(arrangedSubviews: views)
        stack.axis = .vertical; stack.spacing = 10
        stack.isLayoutMarginsRelativeArrangement = true
        stack.directionalLayoutMargins = NSDirectionalEdgeInsets(top: 14, leading: 14, bottom: 14, trailing: 14)
        stack.backgroundColor = highlighted ? highlight : surface
        stack.layer.cornerRadius = 18
        return stack
    }
}
