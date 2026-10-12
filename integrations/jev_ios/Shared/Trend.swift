import Foundation

struct Candle: Equatable, Identifiable {
    var date: String
    var open: Int
    var high: Int
    var low: Int
    var close: Int
    var mine: Int
    var other: Int
    var events: [String]
    var id: String { date }
}

struct Trend: Equatable {
    var title: String
    var candles: [Candle]
    var note: String
}

enum ChatCSV {
    static func records(_ text: String) throws -> [[String]] {
        guard text.utf8.count <= 4_000_000 else { throw GoutouError.invalid("CSV 超过 4 MB，请缩小时间范围") }
        var rows = [[String]](), row = [String](), field = ""
        var quoted = false, closed = false, index = text.startIndex
        while index < text.endIndex {
            let char = text[index]
            let next = text.index(after: index)
            if quoted {
                if char == "\"" {
                    if next < text.endIndex && text[next] == "\"" { field.append("\""); index = text.index(after: next); continue }
                    quoted = false; closed = true
                } else { field.append(char) }
            } else if char == "\"" {
                guard field.isEmpty && !closed else { throw GoutouError.invalid("CSV 引号格式不正确") }
                quoted = true
            } else if char == "," {
                row.append(field); field = ""; closed = false
            } else if char == "\n" || char == "\r\n" || char == "\r" {
                row.append(field)
                if row.contains(where: { !$0.isEmpty }) { rows.append(row) }
                row = []; field = ""; closed = false
            } else {
                guard !closed else { throw GoutouError.invalid("CSV 引号结束后存在多余字符") }
                field.append(char)
            }
            if rows.count > 20_001 { throw GoutouError.invalid("聊天记录超过 20000 条") }
            index = next
        }
        guard !quoted else { throw GoutouError.invalid("CSV 引号未闭合") }
        row.append(field)
        if row.contains(where: { !$0.isEmpty }) { rows.append(row) }
        return rows
    }

    static func load(_ data: Data, title: String = "导入的聊天记录") throws -> Trend {
        guard data.count <= 4_000_000, var text = String(data: data, encoding: .utf8) else { throw GoutouError.invalid("请选择 4 MB 以内的 UTF-8 CSV") }
        if text.hasPrefix("\u{FEFF}") { text.removeFirst() }
        let rows = try records(text)
        guard let header = rows.first, Set(header).count == header.count,
              let timeIndex = header.firstIndex(of: "timestamp"), let senderIndex = header.firstIndex(of: "sender"),
              let messageIndex = header.firstIndex(of: "message"), rows.count > 1, rows.count <= 20_001 else {
            throw GoutouError.invalid("CSV 需要 timestamp,sender,message 三列，且有 1–20000 条消息")
        }
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.timeZone = TimeZone(secondsFromGMT: 0)
        formatter.dateFormat = "yyyy-MM-dd HH:mm:ss"
        formatter.isLenient = false
        let iso = ISO8601DateFormatter()
        let fractional = ISO8601DateFormatter()
        fractional.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        var previous: Date?, candles = [Candle](), balance = 0
        for row in rows.dropFirst() {
            guard row.count == header.count else { throw GoutouError.invalid("CSV 每行的列数必须一致") }
            let raw = row[timeIndex].trimmed
            let naive = formatter.date(from: raw)
            let at = (naive != nil && formatter.string(from: naive!) == raw) ? naive : (iso.date(from: raw) ?? fractional.date(from: raw))
            guard let at = at, raw.count >= 10 else { throw GoutouError.invalid("时间请填 YYYY-MM-DD HH:MM:SS 或带时区的 ISO 8601") }
            if let last = previous, at < last { throw GoutouError.invalid("聊天时间必须按升序排列") }
            previous = at
            let sender = row[senderIndex].trimmed
            guard ["me", "other"].contains(sender), !row[messageIndex].trimmed.isEmpty else {
                throw GoutouError.invalid("请核对双方身份：sender 只能为 me / other，消息不能为空")
            }
            // Normalize timezone-bearing timestamps to UTC before daily grouping.
            let date = String(formatter.string(from: at).prefix(10))
            if candles.last?.date != date { candles.append(Candle(date: date, open: balance, high: balance, low: balance, close: balance, mine: 0, other: 0, events: [])) }
            balance += sender == "other" ? 1 : -1
            let index = candles.count - 1
            candles[index].close = balance
            candles[index].high = max(candles[index].high, balance)
            candles[index].low = min(candles[index].low, balance)
            if sender == "other" { candles[index].other += 1 } else { candles[index].mine += 1 }
            if let eventIndex = header.firstIndex(of: "event"), !row[eventIndex].trimmed.isEmpty {
                guard row[eventIndex].count <= 160 else { throw GoutouError.invalid("事件标注最多 160 字") }
                candles[index].events.append(row[eventIndex].trimmed)
            }
        }
        return Trend(title: title, candles: candles, note: "对方消息 +1，我的消息 −1，按日汇总开、高、低、收。带时区的时间统一按 UTC 分日，无时区时间按原日期处理。仅计算消息净差；结合实际行动解读。原文只在本轮内存中处理，不上传模型。")
    }
}

enum DemoConversation {
    static let text = """
    我：最近项目还那么忙吗
    对方：这周要交方案，白天基本都在开会
    我：辛苦，我今天也改了一下午东西
    对方：今天倒是早一点，刚吃完饭
    我：周末出去换换空气吧，那个展还开着
    对方：这周末可能也要收尾，我现在还说不准
    我：我周六下午比较空，想顺路去看看
    对方：我得先看下周五能不能交完
    我：嗯，你先把手里的事忙完
    对方：这周有点忙，下周再看看吧
    """
    static var advice: Advice {
        Advice(support: "拿不准很正常，这轮先不用急着确认关系。", intent: "可能忙于交付，暂时不能确认周末安排，需要空间和减压。", intentConfidence: 0.62,
            facts: ["对方说这周要交方案，白天基本在开会", "对方没有确认周末时间", "你最后已经表示让对方先忙"],
            hypotheses: ["可能确实忙，也可能尚未决定是否赴约"], unknowns: ["周五能否交完", "下周是否有具体可行时间"],
            strategy: .ease, recommendation: "先接住安排，本轮不再追问具体时间。", nextStep: "等对方有新信息后再判断，给自己一个等待窗口。",
            stopCondition: "明确拒绝或要求停止联系时，停止推进。", question: "",
            candidates: [Candidate(text: "好，你先忙", reason: "接住安排，不再增加追问。", tradeoff: "本轮不会直接确定见面。", weight: 60),
                         Candidate(text: "行，忙完再说", reason: "表达简短，留出空间。", tradeoff: "语气较直接。", weight: 40)],
            decision: nil, rankingStatus: "demo")
    }
}
