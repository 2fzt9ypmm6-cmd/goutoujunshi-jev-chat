import SwiftUI
import UniformTypeIdentifiers

struct TrendView: View {
    @State private var selected = "busy_but_reliable"
    @State private var trend: Trend?
    @State private var importer = false
    @State private var message = ""
    private let cases = [("mutual_warming", "双向升温"), ("hot_then_cool", "热聊后降温"),
                         ("conflict_then_repair", "冲突后修复"), ("busy_but_reliable", "忙但仍兑现"),
                         ("clear_boundary", "明确边界后收线")]

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                VStack(alignment: .leading, spacing: 12) {
                    Text("沿着时间轴看互动与行动").font(.title2.bold())
                    Picker("走势示例", selection: $selected) {
                        ForEach(cases, id: \.0) { item in Text(item.1).tag(item.0) }
                    }
                    HStack {
                        Button("查看示例") { loadExample() }.buttonStyle(.bordered)
                        Button("导入聊天 CSV") { importer = true }.buttonStyle(BrandPrimaryButtonStyle())
                    }
                    Text("CSV 需包含 timestamp,sender,message；sender 为 me / other。可加 event 列标注邀约、兑现或明确边界。")
                        .font(.caption).foregroundStyle(Palette.secondary)
                }.card()
                if let trend = trend {
                    VStack(alignment: .leading, spacing: 12) {
                        Text(trend.title).font(.headline)
                        CandleChart(candles: Array(trend.candles.suffix(180))).frame(height: 270)
                        if trend.candles.count > 180 {
                            Text("共 \(trend.candles.count) 个有消息的日期，图表显示最近 180 个；净差承接此前累计值。")
                                .font(.caption).foregroundStyle(Palette.secondary)
                        }
                        HStack { Label("收高于开", systemImage: "arrow.up.right").foregroundStyle(Palette.chartRise)
                            Label("收低于开", systemImage: "arrow.down.right").foregroundStyle(Palette.chartFall) }.font(.caption)
                        Text(trend.note).font(.callout).foregroundStyle(Palette.secondary)
                        Text("消息净差不代表爱意、关系质量或成功率。对照事件，留意具体行动与边界。")
                            .font(.footnote).foregroundStyle(Palette.secondary)
                    }.card()
                    ForEach(Array(trend.candles.filter { !$0.events.isEmpty }.suffix(180))) { candle in
                        VStack(alignment: .leading, spacing: 6) {
                            Text(candle.date).font(.headline)
                            ForEach(Array(candle.events.enumerated()), id: \.offset) { _, event in Text("• " + event) }
                        }.card()
                    }
                }
                Text(message).font(.footnote).foregroundStyle(Palette.secondary)
            }.padding()
        }.background(Palette.cream)
            .fileImporter(isPresented: $importer, allowedContentTypes: [.commaSeparatedText]) { result in
                do {
                    let url = try result.get()
                    let access = url.startAccessingSecurityScopedResource()
                    defer { if access { url.stopAccessingSecurityScopedResource() } }
                    guard let size = try url.resourceValues(forKeys: [.fileSizeKey]).fileSize, size <= 4_000_000 else {
                        throw GoutouError.invalid("CSV 超过 4 MB")
                    }
                    trend = try ChatCSV.load(Data(contentsOf: url), title: url.deletingPathExtension().lastPathComponent)
                    message = "已在本机计算；原文不上传、不保存为聊天档案。"
                } catch { message = error.localizedDescription }
            }
    }
    private func loadExample() {
        do {
            guard let url = Bundle.main.url(forResource: selected, withExtension: "csv") else {
                throw GoutouError.invalid("示例文件缺失")
            }
            let name = cases.first { $0.0 == selected }?.1 ?? "走势"
            trend = try ChatCSV.load(Data(contentsOf: url), title: name + " · 示例")
            message = "示例来自项目内置虚构聊天，用于解释消息净差和事件；不是用户真实关系记录。"
        } catch { message = error.localizedDescription }
    }
}

struct CandleChart: View {
    let candles: [Candle]
    var body: some View {
        ScrollView(.horizontal) {
            Canvas { context, size in
                guard !candles.isEmpty else { return }
                let low = Double(candles.map(\.low).min() ?? 0) - 1
                let high = max(low + 2, Double(candles.map(\.high).max() ?? 1) + 1)
                let top = 20.0, plot = Double(size.height) - 60
                func y(_ value: Int) -> Double { top + (high - Double(value)) / (high - low) * plot }
                for step in 0...4 {
                    let value = low + (high - low) * Double(step) / 4
                    let height = top + (high - value) / (high - low) * plot
                    var path = Path(); path.move(to: CGPoint(x: 36, y: height)); path.addLine(to: CGPoint(x: size.width, y: height))
                    context.stroke(path, with: .color(.secondary.opacity(0.16)), lineWidth: 1)
                    context.draw(Text(String(format: "%.0f", value)).font(.caption2).foregroundColor(.secondary),
                                 at: CGPoint(x: 15, y: height))
                }
                let width = (Double(size.width) - 42) / Double(candles.count)
                for (index, candle) in candles.enumerated() {
                    let x = 42 + width * (Double(index) + 0.5)
                    let color: Color = candle.close >= candle.open ? Palette.chartRise : Palette.chartFall
                    var wick = Path(); wick.move(to: CGPoint(x: x, y: y(candle.high))); wick.addLine(to: CGPoint(x: x, y: y(candle.low)))
                    context.stroke(wick, with: .color(color), lineWidth: 2)
                    let rect = CGRect(x: x - min(14, width * 0.25), y: min(y(candle.open), y(candle.close)),
                                      width: min(28, width * 0.5), height: max(2, abs(y(candle.open) - y(candle.close))))
                    context.fill(Path(rect), with: .color(color))
                    if !candle.events.isEmpty {
                        context.fill(Path(ellipseIn: CGRect(x: x - 3, y: y(candle.high) - 10, width: 6, height: 6)), with: .color(Palette.chartEvent))
                    }
                    if index % max(1, candles.count / 12) == 0 {
                        context.draw(Text(String(candle.date.suffix(5))).font(.caption2).foregroundColor(.secondary),
                                     at: CGPoint(x: x, y: size.height - 14))
                    }
                }
            }.frame(width: max(330, CGFloat(candles.count) * 44))
                .accessibilityLabel("消息净差 K 线，共 \(candles.count) 天")
        }
    }
}
