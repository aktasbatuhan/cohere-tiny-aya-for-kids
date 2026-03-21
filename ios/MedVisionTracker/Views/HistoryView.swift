import SwiftUI

struct HistoryView: View {
    var body: some View {
        NavigationStack {
            ContentUnavailableView(
                "History Removed",
                systemImage: "clock.arrow.circlepath",
                description: Text("The copied medical-history screen is intentionally not part of the TinyAya MVP.")
            )
            .navigationTitle("History")
        }
    }
}
