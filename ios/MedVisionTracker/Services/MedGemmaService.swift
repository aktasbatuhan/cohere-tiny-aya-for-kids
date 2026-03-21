import Foundation
import Observation
import AVFoundation
import UIKit
@preconcurrency import MLX
import MLXUtilsLibrary
import KokoroSwift
import SwiftWhisper

#if canImport(llama)
import llama
#endif

@MainActor
@Observable
final class MedGemmaService {
    struct ChatMessage: Identifiable, Equatable {
        enum Role: String {
            case assistant
            case user
        }

        let id = UUID()
        let role: Role
        var content: String
    }

    enum LlamaModelOption: String, CaseIterable, Identifiable {
        case tinyAyaQ4KM = "tiny-aya-global-q4_k_m.gguf"

        var id: String { rawValue }

        var displayName: String {
            switch self {
            case .tinyAyaQ4KM:
                return "TinyAya Global (GGUF q4_k_m)"
            }
        }

        var downloadURL: URL {
            switch self {
            case .tinyAyaQ4KM:
                return URL(string: "https://huggingface.co/CohereLabs/tiny-aya-global-GGUF/resolve/main/tiny-aya-global-q4_k_m.gguf?download=true")!
            }
        }
    }

    var selectedLlamaModel: LlamaModelOption = .tinyAyaQ4KM
    var isModelLoaded = false
    var isLoading = false
    var isAnalyzing = false
    var loadingProgress = 0.0
    var loadingStatus = "Model not loaded"
    var errorMessage: String?
    var generatedText = ""
    var memoryUsageMB = 0.0
    var chatMessages: [ChatMessage] = []
    var lastResponseLatencySeconds: Double?
    var isListening = false
    var isSpeaking = false
    var liveTranscript = ""
    var voiceStatus = "Tap the microphone to talk to Aya."
    var microphonePermissionGranted = false
    var autoSpeakResponses = true

    private var loadingLock = false
    @ObservationIgnored private var memoryWarningObserver: NSObjectProtocol?
    @ObservationIgnored private var audioRecorder: AVAudioRecorder?
    @ObservationIgnored private var activeRecordingURL: URL?
    @ObservationIgnored private var audioPlayer: AVAudioPlayer?
    @ObservationIgnored private var activePlaybackURL: URL?
    @ObservationIgnored private var whisper: Whisper?
    @ObservationIgnored private var kokoroEngine: KokoroTTS?
    @ObservationIgnored private var kokoroVoices: [String: MLXArray] = [:]
    @ObservationIgnored private var selectedVoiceKey = "af_heart.npy"

    #if canImport(llama)
    private var llamaContext: TinyAyaLlamaContext?
    private var llamaModelPath: String?
    #endif

    private let maxTokens = 192
    private let systemPrompt = """
    You are Aya, a calm, warm, child-safe AI companion for children ages 4 to 8.
    Use simple language, short sentences, and a friendly tone.
    Avoid harmful, sexual, graphic, hateful, or frightening content.
    If the child asks for unsafe content, gently refuse and redirect to a safe alternative.
    Encourage curiosity, kindness, creativity, and emotional reassurance.
    """

    private let whisperModelURL = URL(string: "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.bin?download=true")!
    private let kokoroModelURL = URL(string: "https://github.com/mlalma/KokoroTestApp/raw/main/Resources/kokoro-v1_0.safetensors")!
    private let kokoroVoicesURL = URL(string: "https://github.com/mlalma/KokoroTestApp/raw/main/Resources/voices.npz")!

    init() {
        setupMemoryWarningObserver()
        seedConversation()
        updateMemoryUsage()
    }

    deinit {
        if let observer = memoryWarningObserver {
            NotificationCenter.default.removeObserver(observer)
        }
    }

    var activeModelDisplayName: String {
        selectedLlamaModel.displayName
    }

    var runtimeSummary: String {
        "Aya runs fully on device with TinyAya, Whisper tiny, and Kokoro."
    }

    func loadModel() async {
        guard !loadingLock && !isLoading && !isModelLoaded else { return }
        loadingLock = true
        defer { loadingLock = false }

        isLoading = true
        errorMessage = nil
        loadingProgress = 0

        do {
            try await loadLlamaModel()
        } catch {
            errorMessage = "Failed to load model: \(error.localizedDescription)"
            loadingStatus = "Model load failed"
            unloadModel()
        }

        isLoading = false
    }

    func unloadModel() {
        #if canImport(llama)
        llamaContext = nil
        llamaModelPath = nil
        #endif

        whisper = nil
        kokoroEngine = nil
        kokoroVoices = [:]
        generatedText = ""
        isModelLoaded = false
        loadingProgress = 0
        loadingStatus = "Model unloaded"
        stopSpeaking()
        updateMemoryUsage()
    }

    func clearConversation() async {
        #if canImport(llama)
        await llamaContext?.clear()
        #endif
        generatedText = ""
        chatMessages.removeAll()
        seedConversation()
        stopSpeaking()
    }

    func sendMessage(_ prompt: String) async {
        let trimmed = prompt.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }
        guard isModelLoaded else {
            errorMessage = "Load the model before chatting."
            return
        }

        errorMessage = nil
        isAnalyzing = true
        generatedText = ""
        chatMessages.append(ChatMessage(role: .user, content: trimmed))
        chatMessages.append(ChatMessage(role: .assistant, content: ""))

        let start = Date()

        do {
            try await streamLlamaResponse()
            lastResponseLatencySeconds = Date().timeIntervalSince(start)
            loadingStatus = "Last response: \(String(format: "%.1f", lastResponseLatencySeconds ?? 0))s"
            updateMemoryUsage()
            if autoSpeakResponses {
                try await speakLatestAssistantReplyIfNeeded()
            }
        } catch {
            if let index = chatMessages.indices.last {
                chatMessages[index].content = "I hit an error while generating a response."
            }
            errorMessage = "Generation failed: \(error.localizedDescription)"
            updateMemoryUsage()
        }

        isAnalyzing = false
    }

    func generateText(prompt: String) async -> String? {
        let trimmed = prompt.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return nil }
        guard isModelLoaded else {
            return "Model not loaded"
        }

        generatedText = ""

        do {
            #if canImport(llama)
            let response = try await llamaContext?.generateResponse(
                prompt: formattedPrompt(appending: trimmed),
                maxTokens: maxTokens
            )
            generatedText = response ?? ""
            #else
            return "llama.cpp runtime not linked"
            #endif

            updateMemoryUsage()
            return generatedText
        } catch {
            return "Error: \(error.localizedDescription)"
        }
    }

    func requestVoicePermissionsIfNeeded() async {
        if !microphonePermissionGranted {
            microphonePermissionGranted = await withCheckedContinuation { continuation in
                AVAudioApplication.requestRecordPermission { granted in
                    continuation.resume(returning: granted)
                }
            }
        }

        voiceStatus = microphonePermissionGranted ? "Voice ready." : "Microphone permission is missing."
    }

    func toggleVoiceInput() async {
        if isListening {
            await stopVoiceCapture(sendTranscript: true)
        } else {
            do {
                try await startVoiceCapture()
            } catch {
                errorMessage = "Voice input failed: \(error.localizedDescription)"
                voiceStatus = "Voice input unavailable."
                teardownRecording()
            }
        }
    }

    func stopSpeaking() {
        audioPlayer?.stop()
        audioPlayer = nil
        if let activePlaybackURL {
            cleanupTemporaryFile(at: activePlaybackURL)
            self.activePlaybackURL = nil
        }
        isSpeaking = false
        try? AVAudioSession.sharedInstance().setActive(false, options: .notifyOthersOnDeactivation)
    }

    func updateMemoryUsage() {
        memoryUsageMB = Self.currentAppMemoryMB()
    }

    private func seedConversation() {
        if chatMessages.isEmpty {
            chatMessages = [
                ChatMessage(
                    role: .assistant,
                    content: "Hi, I'm Aya. I can chat, explain things simply, and talk back once my on-device voice is ready."
                )
            ]
        }
    }

    private func setupMemoryWarningObserver() {
        memoryWarningObserver = NotificationCenter.default.addObserver(
            forName: UIApplication.didReceiveMemoryWarningNotification,
            object: nil,
            queue: .main
        ) { [weak self] _ in
            Task { @MainActor in
                self?.handleMemoryWarning()
            }
        }
    }

    private func handleMemoryWarning() {
        updateMemoryUsage()
    }

    private func startVoiceCapture() async throws {
        await requestVoicePermissionsIfNeeded()
        guard microphonePermissionGranted else {
            throw NSError(domain: "TinyAyaVoice", code: 20, userInfo: [NSLocalizedDescriptionKey: "Microphone permission was not granted"])
        }
        guard isModelLoaded else {
            throw NSError(domain: "TinyAyaVoice", code: 21, userInfo: [NSLocalizedDescriptionKey: "Load TinyAya before using voice"])
        }

        try await prepareWhisperIfNeeded()
        stopSpeaking()
        teardownRecording()
        liveTranscript = ""
        errorMessage = nil
        voiceStatus = "Listening..."

        let audioSession = AVAudioSession.sharedInstance()
        try audioSession.setCategory(.playAndRecord, mode: .measurement, options: [.defaultToSpeaker, .allowBluetoothHFP, .duckOthers])
        try audioSession.setActive(true, options: .notifyOthersOnDeactivation)

        let recordingURL = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString).appendingPathExtension("caf")
        let settings: [String: Any] = [
            AVFormatIDKey: kAudioFormatLinearPCM,
            AVSampleRateKey: 16_000,
            AVNumberOfChannelsKey: 1,
            AVLinearPCMBitDepthKey: 32,
            AVLinearPCMIsFloatKey: true,
            AVLinearPCMIsBigEndianKey: false,
            AVLinearPCMIsNonInterleaved: false
        ]

        let recorder = try AVAudioRecorder(url: recordingURL, settings: settings)
        recorder.prepareToRecord()
        guard recorder.record() else {
            throw NSError(domain: "TinyAyaVoice", code: 22, userInfo: [NSLocalizedDescriptionKey: "Recorder failed to start"])
        }

        audioRecorder = recorder
        activeRecordingURL = recordingURL
        isListening = true
    }

    private func stopVoiceCapture(sendTranscript: Bool) async {
        let recordingURL = activeRecordingURL
        teardownRecording()

        guard sendTranscript, let recordingURL else {
            voiceStatus = "Tap the microphone to talk to Aya."
            return
        }

        do {
            voiceStatus = "Transcribing with Whisper..."
            let audioFrames = try loadRecordedFrames(from: recordingURL)
            cleanupTemporaryFile(at: recordingURL)
            let transcript = try await transcribe(audioFrames: audioFrames)
            liveTranscript = transcript

            let trimmed = transcript.trimmingCharacters(in: .whitespacesAndNewlines)
            if trimmed.isEmpty {
                voiceStatus = "I didn't catch that. Try again."
                return
            }

            voiceStatus = "Sending voice message..."
            await sendMessage(trimmed)
            if !isSpeaking {
                voiceStatus = "Tap the microphone to talk to Aya."
            }
        } catch {
            cleanupTemporaryFile(at: recordingURL)
            errorMessage = "Transcription failed: \(error.localizedDescription)"
            voiceStatus = "Voice transcription failed."
        }
    }

    private func teardownRecording() {
        audioRecorder?.stop()
        audioRecorder = nil
        activeRecordingURL = nil
        isListening = false

        do {
            try AVAudioSession.sharedInstance().setActive(false, options: .notifyOthersOnDeactivation)
        } catch {
            // Ignore teardown failures while iterating.
        }
    }

    private func cleanupTemporaryFile(at url: URL) {
        try? FileManager.default.removeItem(at: url)
    }

    private func loadRecordedFrames(from url: URL) throws -> [Float] {
        let file = try AVAudioFile(forReading: url)
        guard let buffer = AVAudioPCMBuffer(
            pcmFormat: file.processingFormat,
            frameCapacity: AVAudioFrameCount(file.length)
        ) else {
            throw NSError(domain: "TinyAyaVoice", code: 23, userInfo: [NSLocalizedDescriptionKey: "Failed to create audio buffer"])
        }

        try file.read(into: buffer)
        guard let channelData = buffer.floatChannelData else {
            throw NSError(domain: "TinyAyaVoice", code: 24, userInfo: [NSLocalizedDescriptionKey: "Recorded audio was not float PCM"])
        }

        return Array(UnsafeBufferPointer(start: channelData[0], count: Int(buffer.frameLength)))
    }

    private func transcribe(audioFrames: [Float]) async throws -> String {
        try await prepareWhisperIfNeeded()
        guard let whisper else {
            throw NSError(domain: "TinyAyaVoice", code: 25, userInfo: [NSLocalizedDescriptionKey: "Whisper is unavailable"])
        }

        let segments = try await whisper.transcribe(audioFrames: audioFrames)
        return segments.map(\.text).joined(separator: " ")
    }

    private func prepareWhisperIfNeeded() async throws {
        guard whisper == nil else { return }
        let modelURL = try await ensureDownloadedFile(named: "ggml-tiny.bin", from: whisperModelURL)
        let params = WhisperParams(strategy: .greedy)
        params.language = .auto
        params.print_realtime = false
        params.print_progress = false
        params.print_special = false
        params.translate = false
        params.no_context = true
        whisper = Whisper(fromFileURL: modelURL, withParams: params)
    }

    private func prepareKokoroIfNeeded() async throws {
        guard kokoroEngine == nil || kokoroVoices.isEmpty else { return }
        let modelURL = try await ensureDownloadedFile(named: "kokoro-v1_0.safetensors", from: kokoroModelURL)
        let voicesURL = try await ensureDownloadedFile(named: "voices.npz", from: kokoroVoicesURL)

        let voices = NpyzReader.read(fileFromPath: voicesURL) ?? [:]
        guard !voices.isEmpty else {
            throw NSError(domain: "TinyAyaVoice", code: 26, userInfo: [NSLocalizedDescriptionKey: "No Kokoro voices were loaded"])
        }

        kokoroEngine = KokoroTTS(modelPath: modelURL)
        kokoroVoices = voices
        if !kokoroVoices.keys.contains(selectedVoiceKey), let fallback = kokoroVoices.keys.sorted().first {
            selectedVoiceKey = fallback
        }
    }

    private func speakLatestAssistantReplyIfNeeded() async throws {
        guard let reply = chatMessages.last(where: { $0.role == .assistant })?.content.trimmingCharacters(in: .whitespacesAndNewlines), !reply.isEmpty else {
            return
        }
        try await speak(reply)
    }

    private func speak(_ text: String) async throws {
        try await prepareKokoroIfNeeded()
        guard let kokoroEngine else {
            throw NSError(domain: "TinyAyaVoice", code: 27, userInfo: [NSLocalizedDescriptionKey: "Kokoro is unavailable"])
        }
        guard let voice = kokoroVoices[selectedVoiceKey] else {
            throw NSError(domain: "TinyAyaVoice", code: 28, userInfo: [NSLocalizedDescriptionKey: "Selected Kokoro voice is unavailable"])
        }

        let audioSession = AVAudioSession.sharedInstance()
        try audioSession.setCategory(.playback, mode: .spokenAudio, options: [.duckOthers])
        try audioSession.setActive(true, options: .notifyOthersOnDeactivation)

        voiceStatus = "Aya is speaking..."
        isSpeaking = true

        let language: KokoroSwift.Language = selectedVoiceKey.first == "a" ? .enUS : .enGB
        #if canImport(llama)
        releaseLlamaContextForTTS()
        #endif
        let result = try kokoroEngine.generateAudio(voice: voice, language: language, text: text)
        try playAudio(result.0)
    }

    private func playAudio(_ audio: [Float]) throws {
        let playbackURL = FileManager.default.temporaryDirectory
            .appendingPathComponent(UUID().uuidString)
            .appendingPathExtension("wav")
        try writeWaveFile(samples: audio, to: playbackURL)

        stopSpeaking()

        let player = try AVAudioPlayer(contentsOf: playbackURL)
        player.prepareToPlay()
        guard player.play() else {
            cleanupTemporaryFile(at: playbackURL)
            throw NSError(domain: "TinyAyaVoice", code: 29, userInfo: [NSLocalizedDescriptionKey: "Failed to start audio playback"])
        }

        audioPlayer = player
        activePlaybackURL = playbackURL

        Task { @MainActor [weak self] in
            let duration = max(player.duration, 0)
            if duration > 0 {
                try? await Task.sleep(for: .seconds(duration + 0.1))
            }
            guard let self, self.audioPlayer === player else { return }
            self.audioPlayer = nil
            if self.isListening == false {
                self.voiceStatus = "Tap the microphone to talk to Aya."
            }
            self.isSpeaking = false
            if let activePlaybackURL = self.activePlaybackURL {
                self.cleanupTemporaryFile(at: activePlaybackURL)
                self.activePlaybackURL = nil
            }
            try? AVAudioSession.sharedInstance().setActive(false, options: .notifyOthersOnDeactivation)
        }
    }

    private func writeWaveFile(samples: [Float], to url: URL) throws {
        let clamped = samples.map { max(-1, min(1, $0)) }
        let int16Samples = clamped.map { Int16(($0 * Float(Int16.max)).rounded()) }
        let dataSize = int16Samples.count * MemoryLayout<Int16>.size
        let fileSize = 36 + dataSize

        var data = Data(capacity: 44 + dataSize)
        data.append("RIFF".data(using: .ascii)!)
        data.append(UInt32(fileSize).littleEndianData)
        data.append("WAVE".data(using: .ascii)!)
        data.append("fmt ".data(using: .ascii)!)
        data.append(UInt32(16).littleEndianData)
        data.append(UInt16(1).littleEndianData)
        data.append(UInt16(1).littleEndianData)
        data.append(UInt32(KokoroTTS.Constants.samplingRate).littleEndianData)
        data.append(UInt32(KokoroTTS.Constants.samplingRate * 2).littleEndianData)
        data.append(UInt16(2).littleEndianData)
        data.append(UInt16(16).littleEndianData)
        data.append("data".data(using: .ascii)!)
        data.append(UInt32(dataSize).littleEndianData)

        int16Samples.forEach { sample in
            data.append(sample.littleEndianData)
        }

        try data.write(to: url, options: .atomic)
    }

    #if canImport(llama)
    private func loadLlamaModel() async throws {
        loadingStatus = "Checking TinyAya GGUF..."
        let modelURL = try await ensureDownloadedFile(named: selectedLlamaModel.rawValue, from: selectedLlamaModel.downloadURL)

        loadingStatus = "Loading TinyAya runtime..."
        loadingProgress = 1.0
        llamaModelPath = modelURL.path
        llamaContext = try TinyAyaLlamaContext.createContext(path: modelURL.path)
        isModelLoaded = true
        loadingStatus = "TinyAya ready. Whisper and Kokoro load on first voice use."
        updateMemoryUsage()
    }

    private func streamLlamaResponse() async throws {
        let llamaContext = try ensureLlamaContext()

        let prompt = formattedPrompt()
        let stream = try await llamaContext.responseStream(prompt: prompt, maxTokens: maxTokens)

        for try await chunk in stream {
            generatedText += chunk
            if let index = chatMessages.indices.last {
                chatMessages[index].content = generatedText
            }
        }
    }
    #else
    private func loadLlamaModel() async throws {
        throw NSError(domain: "TinyAya", code: 5, userInfo: [NSLocalizedDescriptionKey: "llama.cpp framework not linked"])
    }
    #endif

    #if canImport(llama)
    private func ensureLlamaContext() throws -> TinyAyaLlamaContext {
        if let llamaContext {
            return llamaContext
        }
        guard let llamaModelPath else {
            throw NSError(domain: "TinyAya", code: 4, userInfo: [NSLocalizedDescriptionKey: "llama.cpp model path missing"])
        }
        let context = try TinyAyaLlamaContext.createContext(path: llamaModelPath)
        llamaContext = context
        return context
    }

    private func releaseLlamaContextForTTS() {
        llamaContext = nil
        updateMemoryUsage()
    }
    #endif

    private func ensureDownloadedFile(named name: String, from remoteURL: URL) async throws -> URL {
        let destination = documentsDirectory().appendingPathComponent(name)
        if FileManager.default.fileExists(atPath: destination.path) {
            return destination
        }

        loadingStatus = "Downloading \(name)..."
        let request = URLRequest(
            url: remoteURL,
            cachePolicy: .reloadIgnoringLocalCacheData,
            timeoutInterval: 60 * 60
        )
        let session = makeModelDownloadSession()
        let (temporaryURL, _) = try await session.download(for: request)

        let parent = destination.deletingLastPathComponent()
        try FileManager.default.createDirectory(at: parent, withIntermediateDirectories: true)

        if FileManager.default.fileExists(atPath: destination.path) {
            try FileManager.default.removeItem(at: destination)
        }
        try FileManager.default.moveItem(at: temporaryURL, to: destination)

        return destination
    }

    private func makeModelDownloadSession() -> URLSession {
        let configuration = URLSessionConfiguration.default
        configuration.waitsForConnectivity = true
        configuration.timeoutIntervalForRequest = 60 * 60
        configuration.timeoutIntervalForResource = 60 * 60 * 6
        configuration.requestCachePolicy = .reloadIgnoringLocalCacheData
        return URLSession(configuration: configuration)
    }

    private func documentsDirectory() -> URL {
        FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
    }

    private func formattedPrompt(appending adHocUserPrompt: String? = nil) -> String {
        let relevantMessages = chatMessages.filter { !($0.role == .assistant && $0.content.contains("Whisper and Kokoro")) }
        var prompt = "<BOS_TOKEN><|START_OF_TURN_TOKEN|><|SYSTEM_TOKEN|>\(systemPrompt)<|END_OF_TURN_TOKEN|>"

        for message in relevantMessages {
            switch message.role {
            case .user:
                prompt += "<|START_OF_TURN_TOKEN|><|USER_TOKEN|>\(message.content)<|END_OF_TURN_TOKEN|>"
            case .assistant:
                guard !message.content.isEmpty else { continue }
                prompt += "<|START_OF_TURN_TOKEN|><|CHATBOT_TOKEN|><|START_RESPONSE|>\(message.content)<|END_RESPONSE|><|END_OF_TURN_TOKEN|>"
            }
        }

        if let adHocUserPrompt, !adHocUserPrompt.isEmpty {
            prompt += "<|START_OF_TURN_TOKEN|><|USER_TOKEN|>\(adHocUserPrompt)<|END_OF_TURN_TOKEN|>"
        }

        prompt += "<|START_OF_TURN_TOKEN|><|CHATBOT_TOKEN|><|START_RESPONSE|>"
        return prompt
    }

    private static func currentAppMemoryMB() -> Double {
        var info = mach_task_basic_info()
        var count = mach_msg_type_number_t(MemoryLayout<mach_task_basic_info>.size) / 4
        let result = withUnsafeMutablePointer(to: &info) {
            $0.withMemoryRebound(to: integer_t.self, capacity: Int(count)) {
                task_info(mach_task_self_, task_flavor_t(MACH_TASK_BASIC_INFO), $0, &count)
            }
        }

        guard result == KERN_SUCCESS else { return 0 }
        return Double(info.resident_size) / (1024 * 1024)
    }
}

private extension FixedWidthInteger {
    var littleEndianData: Data {
        var value = littleEndian
        return Data(bytes: &value, count: MemoryLayout<Self>.size)
    }
}

#if canImport(llama)
enum TinyAyaLlamaError: Error {
    case couldNotInitializeContext
}

actor TinyAyaLlamaContext {
    private var model: OpaquePointer
    private var context: OpaquePointer
    private var vocab: OpaquePointer
    private var sampler: UnsafeMutablePointer<llama_sampler>
    private var batch: llama_batch
    private var tokens: [llama_token]
    private var pendingInvalidBytes: [CChar]
    private var isDone = false
    private var currentPosition: Int32 = 0
    private let maxContext: Int32 = 4096

    private init(model: OpaquePointer, context: OpaquePointer) {
        self.model = model
        self.context = context
        self.vocab = llama_model_get_vocab(model)
        self.tokens = []
        self.pendingInvalidBytes = []
        self.batch = llama_batch_init(512, 0, 1)

        let params = llama_sampler_chain_default_params()
        guard let chain = llama_sampler_chain_init(params) else {
            fatalError("Failed to initialize llama sampler chain")
        }
        llama_sampler_chain_add(chain, llama_sampler_init_top_k(40))
        llama_sampler_chain_add(chain, llama_sampler_init_top_p(0.95, 1))
        llama_sampler_chain_add(chain, llama_sampler_init_temp(0.7))
        llama_sampler_chain_add(chain, llama_sampler_init_dist(1234))
        self.sampler = chain
    }

    deinit {
        llama_sampler_free(sampler)
        llama_batch_free(batch)
        llama_model_free(model)
        llama_free(context)
        llama_backend_free()
    }

    static func createContext(path: String) throws -> TinyAyaLlamaContext {
        llama_backend_init()

        var modelParams = llama_model_default_params()
        #if targetEnvironment(simulator)
        modelParams.n_gpu_layers = 0
        #endif

        guard let model = llama_model_load_from_file(path, modelParams) else {
            throw TinyAyaLlamaError.couldNotInitializeContext
        }

        let threadCount = max(1, min(8, ProcessInfo.processInfo.processorCount - 2))
        var contextParams = llama_context_default_params()
        contextParams.n_ctx = 4096
        contextParams.n_threads = Int32(threadCount)
        contextParams.n_threads_batch = Int32(threadCount)

        guard let context = llama_init_from_model(model, contextParams) else {
            llama_model_free(model)
            throw TinyAyaLlamaError.couldNotInitializeContext
        }

        return TinyAyaLlamaContext(model: model, context: context)
    }

    func clear() {
        tokens.removeAll()
        pendingInvalidBytes.removeAll()
        currentPosition = 0
        isDone = false
        llama_memory_clear(llama_get_memory(context), true)
    }

    func generateResponse(prompt: String, maxTokens: Int) async throws -> String {
        let stream = try await responseStream(prompt: prompt, maxTokens: maxTokens)
        var output = ""
        for try await chunk in stream {
            output += chunk
        }
        return output
    }

    func responseStream(prompt: String, maxTokens: Int) async throws -> AsyncThrowingStream<String, Error> {
        try prepare(prompt: prompt)
        let maxTokens = Int32(maxTokens)

        return AsyncThrowingStream { continuation in
            Task.detached(priority: .userInitiated) {
                do {
                    var produced: Int32 = 0
                    while produced < maxTokens {
                        if Task.isCancelled {
                            continuation.finish()
                            return
                        }

                        let piece = try await self.nextTokenPiece()
                        if piece.isEmpty {
                            break
                        }

                        continuation.yield(piece)
                        produced += 1
                    }

                    continuation.finish()
                } catch {
                    continuation.finish(throwing: error)
                }
            }
        }
    }

    private func prepare(prompt: String) throws {
        clear()

        let rawCount = llama_tokenize(vocab, prompt, Int32(prompt.utf8.count), nil, 0, true, true)
        let requiredCount = rawCount < 0 ? -rawCount : rawCount
        guard requiredCount > 0 else {
            throw TinyAyaLlamaError.couldNotInitializeContext
        }

        var promptTokens = Array<llama_token>(repeating: 0, count: Int(requiredCount))
        let written = llama_tokenize(vocab, prompt, Int32(prompt.utf8.count), &promptTokens, requiredCount, true, true)
        guard written >= 0 else {
            throw TinyAyaLlamaError.couldNotInitializeContext
        }

        tokens = Array(promptTokens.prefix(Int(written)))
        currentPosition = 0
        isDone = false

        try decode(tokens: tokens, isPrompt: true)
    }

    private func decode(tokens newTokens: [llama_token], isPrompt: Bool) throws {
        llama_batch_clear(&batch)

        for (index, token) in newTokens.enumerated() {
            let absoluteIndex = currentPosition + Int32(index)
            let logits: Int32 = (index == newTokens.count - 1) ? 1 : 0
            llama_batch_add(&batch, token, absoluteIndex, [0], logits)
        }

        let result = llama_decode(context, batch)
        guard result == 0 else {
            throw TinyAyaLlamaError.couldNotInitializeContext
        }

        currentPosition += Int32(newTokens.count)
        if !isPrompt {
            tokens.append(contentsOf: newTokens)
        }
    }

    private func nextTokenPiece() throws -> String {
        if isDone {
            return ""
        }

        let token = llama_sampler_sample(sampler, context, -1)
        if llama_vocab_is_eog(vocab, token) {
            isDone = true
            return flushPendingBytes()
        }

        try decode(tokens: [token], isPrompt: false)
        return tokenToPiece(token)
    }

    private func tokenToPiece(_ token: llama_token) -> String {
        var buffer = Array<CChar>(repeating: 0, count: 16)
        let pieceLength = Int(llama_token_to_piece(vocab, token, &buffer, Int32(buffer.count), 0, true))
        if pieceLength < 0 {
            buffer = Array<CChar>(repeating: 0, count: -pieceLength)
            let secondPass = llama_token_to_piece(vocab, token, &buffer, Int32(buffer.count), 0, true)
            return stringFromPieceBuffer(buffer, count: Int(secondPass))
        }
        return stringFromPieceBuffer(buffer, count: pieceLength)
    }

    private func stringFromPieceBuffer(_ buffer: [CChar], count: Int) -> String {
        guard count > 0 else { return "" }

        var bytes = pendingInvalidBytes
        bytes.append(contentsOf: buffer.prefix(count))

        if let string = String(validatingUTF8: bytes + [0]) {
            pendingInvalidBytes.removeAll(keepingCapacity: true)
            return string
        }

        pendingInvalidBytes = bytes
        return ""
    }

    private func flushPendingBytes() -> String {
        guard !pendingInvalidBytes.isEmpty else { return "" }
        defer { pendingInvalidBytes.removeAll(keepingCapacity: true) }
        return String(decoding: pendingInvalidBytes.map { UInt8(bitPattern: $0) }, as: UTF8.self)
    }
}

private func llama_batch_clear(_ batch: inout llama_batch) {
    batch.n_tokens = 0
}

private func llama_batch_add(_ batch: inout llama_batch, _ token: llama_token, _ position: Int32, _ sequenceIDs: [Int32], _ logits: Int32) {
    let index = Int(batch.n_tokens)
    batch.token[index] = token
    batch.pos[index] = position
    batch.n_seq_id[index] = Int32(sequenceIDs.count)

    for (sequenceIndex, sequenceID) in sequenceIDs.enumerated() {
        batch.seq_id[index]![sequenceIndex] = sequenceID
    }

    batch.logits[index] = Int8(logits)
    batch.n_tokens += 1
}
#endif
