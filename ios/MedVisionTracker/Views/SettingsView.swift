import SwiftUI

struct SettingsView: View {
    @Environment(AppState.self) private var appState
    @State private var showingDebug = false

    var body: some View {
        NavigationStack {
            List {
                Section("Model") {
                    Picker("Runtime", selection: runtimeBinding) {
                        ForEach(MedGemmaService.RuntimeOption.allCases) { runtime in
                            Text(runtime.displayName).tag(runtime)
                        }
                    }

                    HStack {
                        Text("Checkpoint")
                        Spacer()
                        Text(appState.medGemmaService.activeModelDisplayName)
                            .foregroundStyle(.secondary)
                    }

                    HStack {
                        Text("Status")
                        Spacer()
                        Text(appState.medGemmaService.isModelLoaded ? "Loaded" : "Not loaded")
                            .foregroundStyle(.secondary)
                    }

                    HStack {
                        Text("Backend")
                        Spacer()
                        Text(appState.medGemmaService.selectedRuntime.displayName)
                            .foregroundStyle(.secondary)
                    }

                    HStack {
                        Text("Memory")
                        Spacer()
                        Text("\(Int(appState.medGemmaService.memoryUsageMB)) MB")
                            .foregroundStyle(.secondary)
                    }

                    if let latency = appState.medGemmaService.lastResponseLatencySeconds {
                        HStack {
                            Text("Last response")
                            Spacer()
                            Text(String(format: "%.1fs", latency))
                                .foregroundStyle(.secondary)
                        }
                    }
                }

                Section("Actions") {
                    Button("Load Model") {
                        Task { await appState.medGemmaService.loadModel() }
                    }
                    .disabled(appState.medGemmaService.isLoading || appState.medGemmaService.isModelLoaded)

                    Button("Unload Model") {
                        appState.medGemmaService.unloadModel()
                    }
                    .disabled(!appState.medGemmaService.isModelLoaded)

                    Button("Reset Conversation") {
                        Task { await appState.medGemmaService.clearConversation() }
                    }

                    Button("Open Debug View") {
                        showingDebug = true
                    }
                }

                Section("MVP scope") {
                    Text("This prototype is for iOS-first TinyAya validation: runtime selection, model load, local chat, memory behavior, and response latency.")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }
            }
            .navigationTitle("Settings")
            .sheet(isPresented: $showingDebug) {
                NavigationStack {
                    DebugView()
                        .toolbar {
                            ToolbarItem(placement: .topBarTrailing) {
                                Button("Done") { showingDebug = false }
                            }
                        }
                }
            }
        }
    }

    private var runtimeBinding: Binding<MedGemmaService.RuntimeOption> {
        Binding(
            get: { appState.medGemmaService.selectedRuntime },
            set: { appState.medGemmaService.selectRuntime($0) }
        )
    }
}
