import Foundation

/// A recipient confirmation belongs to one visible keyboard/document/context.
/// Consume it before calling the host proxy so a repeated tap cannot insert twice.
struct DraftInsertion {
    struct Request {
        let text: String
        let documentID: UUID
        let revision: Int
        let relationship: Relationship
        let config: AppConfig
        let createdAt: Date
    }
    private(set) var pending: Request?

    mutating func prepare(text: String, documentID: UUID, revision: Int,
                          relationship: Relationship, config: AppConfig, at date: Date = Date()) throws {
        guard !text.trimmed.isEmpty, text.count <= config.maxCharacters else {
            throw GoutouError.invalid("候选回复为空或超过当前长度设置，请重新生成。")
        }
        pending = Request(text: text, documentID: documentID, revision: revision,
                          relationship: relationship, config: config, createdAt: date)
    }

    mutating func cancel() { pending = nil }

    mutating func consume(documentID: UUID, revision: Int, relationship: Relationship,
                          config: AppConfig, visible: Bool, fullAccess: Bool, hasComposition: Bool,
                          at date: Date = Date()) throws -> String {
        let request = pending
        pending = nil
        guard let request = request, visible, fullAccess, !hasComposition,
              request.documentID == documentID, request.revision == revision,
              request.relationship == relationship, request.config == config,
              (0...60).contains(date.timeIntervalSince(request.createdAt)) else {
            throw GoutouError.invalid("填入确认已过期或输入目标已变化，请重新选择候选并核对收件人。")
        }
        return request.text
    }
}
