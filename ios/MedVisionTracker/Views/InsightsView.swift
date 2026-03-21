import SwiftUI

struct InsightsView: View {
    var body: some View {
        NavigationStack {
            ContentUnavailableView(
                "Insights Coming Later",
                systemImage: "chart.line.uptrend.xyaxis",
                description: Text("The first MVP focuses on local TinyAya chat, memory, and latency on iPhone.")
            )
            .navigationTitle("Insights")
        }
    }
}
