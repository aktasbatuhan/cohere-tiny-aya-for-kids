import SwiftUI

@main
struct TinyAyaKidsApp: App {
    @State private var appState = AppState()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environment(appState)
        }
    }
}

@MainActor
@Observable
final class AppState {
    var tinyAyaService = TinyAyaService()
}
