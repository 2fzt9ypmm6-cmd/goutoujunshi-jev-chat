<p><a href="./README.md">简体中文</a> · English</p>

# Goutoujunshi · iOS keyboard source preview

Offline Chinese Pinyin/English typing and a user-invoked reply assistant inside an iPhone keyboard, plus a companion app for provider settings, selected-image recognition, relationship context, detailed analysis and CSV candlesticks. Minimum iOS 16.

This port adapts the keyboard architecture from [Jev iOS](https://github.com/jev-chat/jev-chat-jarvis-ios), retaining Goutoujunshi's relationship guidance, natural voice, evidence separation and stop conditions. It uses cream, warm orange and a Shiba mascot. **This is a source preview, with no public signed IPA, TestFlight or App Store release. The app and keyboard extension build successfully for the simulator and iPhone; personal iPhone signing, installation and app launch have been verified; complete host-app keyboard behavior remains to be tested.**

## Latest changes · 2026-10-12

- Removed the visible attribution section from settings; repository licenses, attribution and Pinyin licensing are retained.
- Shortcut/image handoffs follow the selected OCR provider. DeepSeek/OpenRouter images return for preview before explicit upload confirmation.
- A fixed five-minute local session restores the latest transcript/advice after dismissal or process recreation; context/configuration changes invalidate it.
- Recipient confirmation and candidate reasons use in-keyboard views to avoid extension crashes; insertion returns to this keyboard’s typing layout.

The October 12 update passed device compilation and signature verification, was installed over the existing app, and launched on a personal iPhone. All 225 offline checks passed; no live model requests or sent chat messages were used. Complete interactions in each host chat app still require separate validation.

## Install from source

1. Install full Xcode 15 or later. Command Line Tools alone cannot build an iOS application.
2. Open GoutouJunshi.xcodeproj. Edit [Signing.xcconfig](Signing.xcconfig) with your developer Team ID, a unique App Bundle ID and an App Group registered to that team. Extension IDs add .keyboard and .capture automatically.
3. All three targets require the same Team and App Group. GoutouJunshi and GoutouKeyboard also share a Keychain group; GoutouCapture does not access credentials. Enable the capabilities and provisioning profiles in your account. The shared keychain group uses AppIdentifierPrefix plus the app ID by default.
4. Select the GoutouJunshi scheme. Check the companion app on an iPhone simulator, then sign and run on an iPhone; follow Xcode's Developer Mode prompts. Distribution requires valid signing and the appropriate Apple review.
5. Open the app's settings, fill your own keys, and save. In iOS Settings → General → Keyboard → Keyboards, add 狗头军师. Switch to it with the globe button in a chat to type locally; enable Full Access when you want to use the online assistant.

A free Apple Account can use a Personal Team in Xcode to test on personal devices. Provisioning profiles expire after seven days and require rebuilding and reinstalling. This project's shared-group signing and keyboard behavior still need device validation. TestFlight distribution requires the publisher to join the Apple Developer Program; the first external-testing build requires beta review. Testers do not need developer membership. See [Apple's account guide](https://developer.apple.com/help/account/basics/about-your-developer-account) and [TestFlight guide](https://developer.apple.com/testflight/).

Full Access enables assistant networking and shared settings; offline typing does not require it. It does not trigger background chat reading. App Group failures are visible errors; the app never silently falls back to an unshared store. Saved keys are not shown; a blank field keeps the existing key. Each provider has a delete-key button.

Host apps can disable custom keyboards; secure and certain phone fields use the system keyboard. Compatibility with specific chat apps needs device testing. See [Apple's keyboard documentation](https://developer.apple.com/library/archive/documentation/General/Conceptual/ExtensibilityPG/CustomKeyboard.html).

## Offline typing

The keyboard opens in Typing mode, with fixed QWERTY rows outside the assistant scroll view, a separate horizontally scrolling candidate bar, a wider space key and compact landscape sizing. Enter full Pinyin, such as nihao, and choose 你好; space accepts the first complete candidate. Candidate words scroll horizontally, continuous Pinyin can be segmented, and 分词 inserts an apostrophe syllable boundary (xi'an). Partial word selection leaves the remaining Pinyin in the preedit buffer. Backspace edits that buffer first and supports hold-to-repeat. Pinyin is only inserted into the host after selection.

The bottom 中 or 英 key switches languages. English supports upper/lower case; 123 opens numbers, #+= opens symbols, and ABC returns to letters. Common emoji and caret arrows are available. 换行 inserts a newline rather than sending a message. Local typing works without Full Access, makes no model requests, and stores no input history or personal vocabulary. Full Access is needed for the assistant's networking and shared settings.

The 65,125-entry dictionary is derived from [Rime pinyin-simp](https://github.com/rime/rime-pinyin-simp), pinned with its Apache-2.0 license and author attribution; the keyboard bundle includes the license. The lightweight decoder currently supports basic full Pinyin, without nine-key input, dictation, personal frequency learning or advanced typo correction.

## Configure models

- **DeepSeek only:** choose the shortcut that sets judgment and replies to DeepSeek, enter your DeepSeek Key and an available model ID, test and save. The project default is deepseek-flash, editable to match your account. Use local Apple Vision OCR if you want selected screenshots to remain on-device. Cloud recognition requires an image-capable model.
- **Jev judgment:** select TypeSafe Jev and save its separate key/model ID. Requests use the official systemone endpoint. Failure is surfaced instead of switching providers.
- **OpenRouter replies:** select OpenRouter, fill its own key and reply-model ID. Image recognition has a separate vision-model ID. OpenRouter is used for replies/vision here; judgment uses DeepSeek or Jev.

Provider endpoints are fixed to their official hosts and credentials stay separate. Tests use the currently typed fields before saving. A connection test consumes API usage and does not prove full JSON or image compatibility.

The independent DeepSeek pipeline extracts evidence, checks first-token logprobs across three A–G label rotations, then generates structured analysis and ranks candidates. Seven labels must be present with a unique matching winner across all rounds and the evidence judgment. Otherwise it keeps the evidence judgment and labels token weights unavailable. A normal multi-candidate analysis makes six requests; evidence format repair can add one. Explicit stop-contact evidence skips the token checks and forbids advancing drafts. Ranking failure preserves drafts without invented weights.

## Use in chat

**Start with a screenshot:** take a chat screenshot, open the companion app → Use → 从截图读取聊天, and select it from Photos. File selection and explicit screenshot paste are also available. The app displays the image preview and OCR text for review before analysis and optional handoff to the keyboard.

**Recognize inside the keyboard:** in Photos, open the chat screenshot → Share → Copy Photo. Return to the chat and tap the keyboard's top capture button or 截图识别 in Assistant mode. Choose Read copied screenshot, then Recognize in local mode. Cloud mode shows a preview and waits for explicit upload confirmation. Apple Vision runs locally; DeepSeek/OpenRouter requires confirmation before uploading each screenshot. Clipboard access requires Full Access. The keyboard does not browse the photo library or capture other apps' screens automatically.

Recognition always opens transcript review before analysis. Bubble position is only a tentative speaker cue; centered labels remain marked unresolved. Tap a reviewed line to change its speaker or omit non-chat text. Correct OCR errors in the companion app if needed. “Copy original for review” lets you edit it in the companion app without inserting it into a chat draft. Images are downsampled and re-encoded without original location metadata, and previews/images stay in memory.

Copy a message, switch to the keyboard, tap 军师 (Assistant), and then Read clipboard. Review the transcript, speaker and manually selected recipient. Confirm before analysis. The keyboard also reads only the system-provided text immediately before the input caret; it cannot retrieve chat history.

Results show possible intent, confidence, advice, 1–3 ranked drafts and reasons/tradeoffs. Details separate facts, hypotheses, unknowns, your feelings, next steps and stop conditions. “More like me” rewrites only drafts using verified lines marked as yours in the current transcript.

Fill shows recipient and candidate confirmation inside the keyboard, without a system alert. It inserts once at the current caret, preserving existing text, then returns to GoutouJunshi's own typing layout. The round remains available under 军师. Confirmation expires after 60 seconds and requires the same visible keyboard, document, relationship and configuration; repeated taps cannot duplicate insertion. The keyboard cannot verify a WeChat/Soul recipient. Check the object after changing conversations. **You send from the host app.** The globe button switches to another keyboard.

For multiple messages, paste reviewed text or select screenshots in the companion app. Apple Vision runs locally; DeepSeek/OpenRouter image recognition asks permission before sending each selected image. Correct OCR and label each message as 我： or 对方： before analysis. Explicitly handing a result to the keyboard creates a one-time local transfer valid for five minutes.

## Keyboard system capture (experimental)

In a chat, switch to the keyboard → top 识图 button → 屏幕捕获（实验） → system circular capture button → confirm Start Broadcast in the iOS sheet. The ReplayKit extension processes one video frame, crops the keyboard area, and follows the OCR setting: local Vision returns text; cloud OCR returns an image for preview and upload confirmation in the keyboard. The extension then stops. It has no network client or credential access and does not process audio. No automatic analysis or draft insertion follows.

The user-armed request expires in 90 seconds; use Prepare capture again to retry. Up to 12,000 characters are passed through a backup-excluded App Group file, consumed once within five minutes. A pending cloud JPEG is limited to 4 MB and five minutes, deleted after recognition succeeds, cancellation or context/config changes. It is never uploaded automatically. Expired files are deleted on the next access. This experimental entry targets iOS 16–26 and requires Full Access plus per-session system confirmation. Apple's iOS 27 SDK marks the broadcast API no longer supported, so iOS 27 shows the Shortcuts/copied-image alternatives. Device capture and keyboard return still require verification; protected screens may be unavailable. See [Apple ReplayKit security](https://support.apple.com/guide/security/replaykit-security-seca5fc039dd/web).

## System screenshot directly to keyboard review

The top **识图** button prepares the keyboard to receive text; it cannot directly trigger another app's system screenshot. Open the companion app → Use → 设置一键截屏识别 for setup instructions.

1. Create or edit the 截图问军师 shortcut.
2. Add system Take Screenshot, followed by **狗头军师 → 截图交给键盘（按配置）**. Existing 截图交给键盘（本地） actions retain their identity and now follow the OCR setting; rebuilding the shortcut is unnecessary.
3. Pass the preceding screenshot to the image parameter. Do not add Open App or clipboard steps.
4. Bind the shortcut to AssistiveTouch double-tap or Back Tap in Accessibility settings.
5. Switch to the Goutou keyboard in a chat, tap 识图, and trigger the shortcut within 90 seconds. Apple Vision returns text directly. DeepSeek/OpenRouter returns an image preview; tap 发送截图并识别 to invoke the selected service. The companion app stays closed.

This background action follows the configured OCR provider and excludes the bottom keyboard region. DeepSeek uses the selected DeepSeek model/key; OpenRouter uses its separate vision model/key. The model must support image inputs. Cloud failures surface without a local fallback. Only visible chat is captured. Local text is limited to 12,000 characters; pending cloud JPEGs to 4 MB. Both use protected, backup-excluded App Group files valid for five minutes. Text is consumed once; a pending image survives keyboard recreation until recognition succeeds or it is canceled. Expiry is cleaned on next access. Context/config changes clear the request. Review speakers and text before manually analyzing. The first shortcut run may require system confirmation.

Dismissing the keyboard preserves the pending request and the latest recognized transcript/advice. Reopen the chat input and switch to GoutouJunshi to resume the round, even if iOS recreated the keyboard process. A backup-excluded local session expires five minutes after its content changes; reopening does not extend this lifetime. Images, typing history and confirmation state are excluded. Review the current recipient again; no automatic analysis or insertion follows. Clear Round, settings changes and recipient changes delete the previous session.

**识别聊天截图（按配置）** opens companion-app review and follows the same local/cloud setting, asking upload confirmation for cloud OCR. Existing 识别聊天截图（本地） shortcuts keep the same action identity with the new behavior. Choose 截图交给键盘 to return to the keyboard instead. Runtime behavior in real host apps still requires device verification.

## Context, weights and charts

The app provides seven relationship stages, six goals and limited background/notes. Current context is saved when you press Save; only opting into profile storage adds it to the keyboard's selectable list, up to 100 profiles. No complete chat archive is created.

Intent confidence is an uncalibrated model estimate. Strategy weights are a Jev distribution or checked DeepSeek token weights. Candidate percentages normalize separate relative recommendation scores to 100%; a single candidate receives 100% of that set. None is a verified intent, reply-success or relationship-outcome probability.

The app includes five fictional chart cases and local UTF-8 CSV import, up to 4 MB / 20,000 messages. Required columns: timestamp,sender,message; sender is me or other, optional event adds annotations. Rows must be time-ordered; quoted commas and multiline fields are supported. Each me message is -1 and other message +1; daily cumulative balance forms OHLC candles. Naive dates keep their entered day, zoned ISO timestamps group in UTC. The latest 180 active days are plotted. Imported text is neither uploaded nor archived. Message balance does not measure affection or relationship quality.

## Data and validation

Keys use a shared, device-only Keychain group. App Group UserDefaults holds settings and explicitly saved context. Companion-app transcripts/results stay in memory unless handed to the keyboard or returned by an invoked screenshot action. Text transfer files are consumed once and deleted. The keyboard keeps a separate backup-excluded, five-minute session for the latest explicitly read transcript/advice so dismissal and process recreation do not erase a round; that session excludes images, typing history and confirmation state. A pending cloud OCR JPEG is stored separately in a protected, backup-excluded mailbox for up to five minutes / 4 MB, deleted on successful recognition or cancellation. Reopening does not extend expiry; expired files are cleaned on next access because iOS cannot guarantee background deletion at an exact deadline. Clear Round or settings can delete it immediately. Configuration/recipient changes invalidate previous sessions and handoffs. Keychain items may survive uninstall; delete unwanted keys before uninstalling.

There is no telemetry or project-operated proxy. Confirmed analysis goes directly to the selected providers, whose own terms apply. Canceling drops stale results and prevents later stages; it cannot recall requests already sent. See [PRIVACY.md](../../PRIVACY.md).

Run bash tools/check.sh for shared-core compilation, offline mocked-provider checks, UI syntax parsing and project/resource validation. Regenerate with python3 tools/generate_project.py; refresh bundled guidance with python3 tools/sync_guidance.py.

2026-10-11 draft insertion crash fix: a build-11 device report showed UIAlertController initialization in confirmInsert triggering _UIApplicationAssertForExtensionType and SIGABRT. Build 12 uses in-keyboard recipient confirmation and candidate explanations. Confirm inserts once, returns to GoutouJunshi typing and retains the advice round. New checks cover cancellation, fixed confirmation expiry, changed document/context/config, hidden keyboard and lost permissions; project validation prevents system alerts in the keyboard. All 225 offline checks passed (165 core, 33 typing, 27 OCR), along with simulator/signed-device builds and signature verification; the update was installed on the personal iPhone. Phone use disconnected mirroring, so complete host-app insertion and continued typing still await a direct-phone retry. No live models or sent chat messages were used.

2026-10-11 OCR routing fix: build 11 removes hardcoded Apple Vision from screenshot shortcuts and experimental capture. Cloud settings now return an image preview for explicit upload to the selected model. All 209 offline checks passed (149 core, 33 typing, 27 OCR), covering image handoff, preview restoration, expiry/cancellation, provider/model requests, missing keys and errors without local fallback. Simulator and signed iPhone builds and signature verification passed; the update was installed on the personal iPhone. The device use page still showed DeepSeek selected and the guide showed the configured-provider flow. No private screenshot or live model request was sent; the complete host-app capture-to-cloud path still needs a direct-phone retry.

2026-10-11 keyboard dismissal fix: build 10 passed simulator and signed iPhone builds plus signature verification and was installed on the personal iPhone. All 175 offline checks passed (123 core, 33 typing, 19 OCR). New checks cover restoration across process recreation, fixed expiry, context/configuration invalidation, corrupt files and capture delivery while the keyboard is closed. Direct-phone dismissal/reopening UI validation is still awaiting user confirmation; this update made no live model requests.

With full Xcode, use DEVELOPER_DIR to select Xcode for this command without changing the system's Command Line Tools selection:

    DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer xcodebuild -project GoutouJunshi.xcodeproj -scheme GoutouJunshi -destination 'generic/platform=iOS Simulator' -derivedDataPath build CODE_SIGNING_ALLOWED=NO build

That command checks compilation only. To preview App Group storage in the simulator, use local ad-hoc signing. It needs no Apple signing certificate and does not enable iPhone installation:

    DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer xcodebuild -project GoutouJunshi.xcodeproj -scheme GoutouJunshi -destination 'generic/platform=iOS Simulator' -derivedDataPath build CODE_SIGN_STYLE=Manual CODE_SIGN_IDENTITY=- CODE_SIGNING_ALLOWED=YES build

Install an iOS simulator runtime in Xcode, select an iPhone simulator and run. Xcode 27 uses Xcode → Open Developer Tool → Device Hub, also accessible via Manage Devices in the run-destination menu. An unsigned simulator app may show disconnected App Group storage.

For an unsigned iPhone device build:

    DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer xcodebuild -project GoutouJunshi.xcodeproj -scheme GoutouJunshi -destination 'generic/platform=iOS' -derivedDataPath build-device CODE_SIGNING_ALLOWED=NO build

Outputs are build/Build/Products/Debug-iphonesimulator/GoutouJunshi.app and build-device/Build/Products/Debug-iphoneos/GoutouJunshi.app. Each embeds PlugIns/GoutouKeyboard.appex.

On 2026-10-11, version 0.1.0 (build 4) passed simulator and signed iPhone builds and signature verification, and was installed and launched on a personal iPhone. In the simulator, a two-action Take Screenshot → 识别聊天截图（本地） shortcut automatically connected its image input, recognized the captured screen and opened transcript review with confirmation still disabled. The redesigned keyboard converted nihao to 你好 and inserted the selected candidate. All 136 offline checks passed without live model calls. Physical-device AssistiveTouch/Back Tap binding, screenshots inside actual chat apps and keyboard OCR still require user validation.

On 2026-10-11, the app gained a dedicated screenshot card, preview and image paste. The keyboard gained an image button, explicit clipboard-image recognition and transcript review. **88 core, 33 Pinyin and 15 screenshot/OCR checks passed.** OCR checks use generated Chinese chat pixels and cover reading order, tentative speaker attribution, unresolved labels, downsampling, orientation, metadata removal, invalid images and cancellation. Both targets built for the simulator and signed iPhone; version 0.1.0 (build 3) was installed and launched on a personal iPhone. The simulator Photos workflow recognized three Chinese messages with tentative left/right attribution and marked a centered heading unresolved. Keyboard OCR inside physical-device chat apps and live vision providers remain unverified; no live model requests were made.

On 2026-10-10, all **88 core checks and 33 offline Pinyin checks passed**. The updated app and keyboard extension built for the simulator and signed iPhone, passed signature verification, and version 0.1.0 (build 2) was installed and launched on a personal iPhone. With Full Access disabled in the simulator, the custom keyboard converted nihao to 你好 and inserted it into the companion app's text editor. English, numbers, backspace, space, newline and Assistant/Typing switching were also verified. **Typing in actual chat apps on the physical iPhone, shared Keychain access and live providers remain unverified.** No real keys or model calls were used in this check.

Historical validation on 2026-10-08: **Xcode 27.0 / iOS 27.0 SDK builds passed** for the app and keyboard extension: arm64/x86_64 simulator and unsigned arm64 iPhone device. All 88 offline core checks and syntax/metadata checks passed. The [first GitHub source build on October 12](https://github.com/shengjidaguai-china/goutoujunshi-jev-chat/actions/runs/38209076299) subsequently passed offline checks, simulator and unsigned-device builds, and simulator-app archiving. That artifact is for development only; iPhone installation requires your own valid signing. Those unsigned device builds cannot be installed directly on an iPhone.

The companion app also launches on an iPhone 17 / iOS 27.0 simulator. Offline analysis/details, the provider settings screen, configuration saving and an example candlestick chart were checked. App Group storage connects with local ad-hoc signing. No real keys or live provider requests were used, and keyboard Full Access was not enabled in this check.

An earlier unsigned iPhone Release IPA was also packaged locally, with the app, embedded keyboard, arm64 architecture and archive layout checked. That old package does not include this typing update. It has no signing or device provisioning profile, cannot be installed directly or uploaded to TestFlight, and has not been published as a GitHub Release.

## Attribution

Original additions use the repository's [MIT License](../../LICENSE). Preserve the Jev iOS [LICENSE](vendor/LICENSE), [NOTICE](vendor/NOTICE) and [source revision](vendor/UPSTREAM.json). Relationship/natural-voice excerpts come from this repository's references directory; the generator records their paths. This project is independent of Jev's authors, Apple and chat platforms.

Pinyin dictionary licensing: [Apache-2.0](vendor/pinyin-simp/LICENSE), [authors](vendor/pinyin-simp/AUTHORS), [pinned source](vendor/pinyin-simp/UPSTREAM.json). Rebuild the runtime dictionary with python3 tools/build_pinyin.py.

2026-10-11 experimental keyboard capture: build 8 passed simulator and signed iPhone builds and was installed on the personal iPhone. All 151 offline checks passed (103 core, 33 typing, 15 OCR). Three-target embedding/signing and the no-keychain/no-network-client capture target were checked. System frame capture, return to keyboard and candidate insertion await direct-phone user verification; no live model requests were made in this update.
