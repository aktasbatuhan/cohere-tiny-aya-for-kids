import SwiftUI

struct DebugView: View {
    @Environment(AppState.self) private var appState
    @State private var inputText = "Tell me a fun fact about dolphins."
    @State private var outputText = ""
    @State private var isGenerating = false

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 16) {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Model Status")
                            .font(.headline)

                        HStack {
                            Circle()
                                .fill(appState.medGemmaService.isModelLoaded ? .green : .gray)
                                .frame(width: 10, height: 10)
                            Text(appState.medGemmaService.loadingStatus)
                                .font(.caption)
                        }

                        Picker("Runtime", selection: runtimeBinding) {
                            ForEach(MedGemmaService.RuntimeOption.allCases) { runtime in
                                Text(runtime.displayName).tag(runtime)
                            }
                        }
                        .pickerStyle(.segmented)

                        if appState.medGemmaService.isLoading {
                            ProgressView(value: appState.medGemmaService.loadingProgress)
                        }

                        Text("Memory: \(Int(appState.medGemmaService.memoryUsageMB))MB")
                            .font(.caption)
                            .foregroundStyle(.secondary)

                        HStack {
                            Button("Load Model") {
                                Task { await appState.medGemmaService.loadModel() }
                            }
                            .buttonStyle(.borderedProminent)
                            .disabled(appState.medGemmaService.isLoading || appState.medGemmaService.isModelLoaded)

                            Button("Unload") {
                                appState.medGemmaService.unloadModel()
                            }
                            .buttonStyle(.bordered)
                            .disabled(!appState.medGemmaService.isModelLoaded)

                            Button("Clear Chat") {
                                Task { await appState.medGemmaService.clearConversation() }
                            }
                            .buttonStyle(.bordered)
                        }
                    }
                    .padding()
                    .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 12))

                    VStack(alignment: .leading, spacing: 8) {
                        Text("Prompt")
                            .font(.headline)

                        TextEditor(text: $inputText)
                            .frame(minHeight: 100)
                            .padding(8)
                            .background(Color(.systemGray6))
                            .cornerRadius(8)

                        Button {
                            Task { await generateResponse() }
                        } label: {
                            HStack {
                                if isGenerating {
                                    ProgressView()
                                        .scaleEffect(0.8)
                                }
                                Text(isGenerating ? "Generating..." : "Generate")
                            }
                            .frame(maxWidth: .infinity)
                        }
                        .buttonStyle(.borderedProminent)
                        .disabled(!appState.medGemmaService.isModelLoaded || isGenerating || inputText.isEmpty)
                    }
                    .padding()
                    .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 12))

                    VStack(alignment: .leading, spacing: 8) {
                        HStack {
                            Text("Output")
                                .font(.headline)
                            Spacer()
                            Text("\(outputText.count) chars")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }

                        Text(outputText.isEmpty ? "Response will appear here..." : outputText)
                            .font(.system(.body, design: .monospaced))
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .padding()
                            .background(Color(.systemGray6))
                            .cornerRadius(8)
                    }
                    .padding()
                    .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 12))
                }
                .padding()
            }
            .navigationTitle("Debug")
        }
    }

    private var runtimeBinding: Binding<MedGemmaService.RuntimeOption> {
        Binding(
            get: { appState.medGemmaService.selectedRuntime },
            set: { appState.medGemmaService.selectRuntime($0) }
        )
    }

    private func generateResponse() async {
        isGenerating = true
        outputText = ""
        let response = await appState.medGemmaService.generateText(prompt: inputText)
        outputText = response ?? "Error generating response"
        isGenerating = false
    }
}
