import SwiftUI

struct AnalysisResultsView: View {
    var body: some View {
        ContentUnavailableView(
            "Analysis Results Removed",
            systemImage: "doc.text.magnifyingglass",
            description: Text("The MVP uses text chat rather than medical-image analysis.")
        )
    }
}
