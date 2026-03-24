import SwiftUI

struct AnalysisView: View {
    @Environment(AppState.self) private var appState
    @State private var draft = ""

    private let starterPrompts = [
        "Tell me a bedtime story about a kind moon.",
        "Why do birds sing?",
        "Can we play a guessing game?"
    ]

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                header

                ScrollView {
                    LazyVStack(spacing: 12) {
                        if appState.tinyAyaService.chatMessages.isEmpty {
                            EmptyConversationCard()
                        }

                        ForEach(appState.tinyAyaService.chatMessages) { message in
                            ChatBubble(message: message)
                        }
                    }
                    .padding(.horizontal)
                    .padding(.top, 12)
                    .padding(.bottom, 24)
                }

                quickPrompts
                composer
            }
            .background(
                LinearGradient(
                    colors: [Color.orange.opacity(0.08), Color.yellow.opacity(0.05), Color(.systemGroupedBackground)],
                    startPoint: .top,
                    endPoint: .bottom
                )
            )
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .principal) {
                    Text("Aya")
                        .font(.headline)
                }
            }
            .task {
                await appState.tinyAyaService.requestVoicePermissionsIfNeeded()
            }
        }
    }

    private var header: some View {
        VStack(spacing: 16) {
            HStack(alignment: .center, spacing: 14) {
                ZStack {
                    Circle()
                        .fill(Color.orange.opacity(0.18))
                        .frame(width: 56, height: 56)

                    Image(systemName: appState.tinyAyaService.isListening ? "waveform.circle.fill" : "face.smiling.fill")
                        .font(.system(size: 28))
                        .foregroundStyle(Color.orange)
                }

                VStack(alignment: .leading, spacing: 4) {
                    Text("Aya")
                        .font(.title3.weight(.semibold))
                    Text("Offline voice companion")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                    Text(appState.tinyAyaService.loadingStatus)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    Text(appState.tinyAyaService.voiceStatus)
                        .font(.caption)
                        .foregroundStyle(appState.tinyAyaService.isListening ? .red : .secondary)
                }

                Spacer()

                Button(appState.tinyAyaService.isModelLoaded ? "Ready" : "Load Aya") {
                    Task { await appState.tinyAyaService.loadModel() }
                }
                .buttonStyle(.borderedProminent)
                .disabled(appState.tinyAyaService.isLoading || appState.tinyAyaService.isModelLoaded)
            }

            if appState.tinyAyaService.isLoading {
                ProgressView(value: appState.tinyAyaService.loadingProgress)
            }

            if let error = appState.tinyAyaService.errorMessage {
                Text(error)
                    .font(.caption)
                    .foregroundStyle(.red)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }

            VStack(spacing: 10) {
                Button {
                    Task { await appState.tinyAyaService.toggleVoiceInput() }
                } label: {
                    HStack(spacing: 10) {
                        Image(systemName: appState.tinyAyaService.isListening ? "stop.circle.fill" : "mic.circle.fill")
                            .font(.system(size: 22, weight: .semibold))
                        Text(appState.tinyAyaService.isListening ? "Stop And Send" : "Talk To Aya")
                            .fontWeight(.semibold)
                    }
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 14)
                }
                .buttonStyle(.borderedProminent)
                .tint(appState.tinyAyaService.isListening ? .red : .orange)
                .disabled(!appState.tinyAyaService.isModelLoaded || appState.tinyAyaService.isAnalyzing)

                if !appState.tinyAyaService.liveTranscript.isEmpty {
                    Text(appState.tinyAyaService.liveTranscript)
                        .font(.subheadline)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(12)
                        .background(Color.orange.opacity(0.08), in: RoundedRectangle(cornerRadius: 12))
                }
            }
        }
        .padding()
        .background(.ultraThinMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 24, style: .continuous))
        .padding(.horizontal, 12)
        .padding(.top, 12)
    }

    private var quickPrompts: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 10) {
                ForEach(starterPrompts, id: \.self) { prompt in
                    Button(prompt) {
                        draft = prompt
                    }
                    .buttonStyle(.bordered)
                }
            }
            .padding(.horizontal)
            .padding(.vertical, 10)
        }
        .background(Color(.secondarySystemGroupedBackground))
    }

    private var composer: some View {
        HStack(alignment: .bottom, spacing: 12) {
            TextField("Type if you don’t want to talk...", text: $draft, axis: .vertical)
                .textFieldStyle(.roundedBorder)
                .lineLimit(1...4)

            Button("Send") {
                let message = draft
                draft = ""
                Task { await appState.tinyAyaService.sendMessage(message) }
            }
            .buttonStyle(.borderedProminent)
            .disabled(
                draft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ||
                !appState.tinyAyaService.isModelLoaded ||
                appState.tinyAyaService.isAnalyzing
            )
        }
        .padding()
        .background(.thinMaterial)
    }
}

private struct ChatBubble: View {
    let message: TinyAyaService.ChatMessage

    var body: some View {
        HStack {
            if message.role == .assistant {
                content
                Spacer(minLength: 48)
            } else {
                Spacer(minLength: 48)
                content
            }
        }
    }

    private var content: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(message.role == .assistant ? "Aya" : "You")
                .font(.caption)
                .foregroundStyle(.secondary)
            Text(message.content.isEmpty ? "..." : message.content)
                .font(.body)
        }
        .padding(12)
        .background(
            message.role == .assistant ? Color.orange.opacity(0.10) : Color.blue.opacity(0.10),
            in: RoundedRectangle(cornerRadius: 16)
        )
    }
}

private struct EmptyConversationCard: View {
    var body: some View {
        VStack(spacing: 10) {
            Text("Aya is ready")
                .font(.headline)
            Text("Start talking or type a message when Aya is loaded.")
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
        }
        .frame(maxWidth: .infinity)
        .padding(24)
        .background(Color.orange.opacity(0.08), in: RoundedRectangle(cornerRadius: 18))
    }
}
