document.getElementById("reviewForm").addEventListener("submit", async function(e) {
    e.preventDefault();
    const review = document.getElementById("reviewInput").value.trim();
    const photo = document.getElementById("photoInput").files[0];

    const formData = new FormData();
    if (review) formData.append("review", review);
    if (photo) formData.append("photo", photo);

    const resultDiv = document.getElementById("result");
    resultDiv.className = ""; // Clear previous styling/classes
    resultDiv.innerHTML = "Analyzing..."; // Temporary loading message
    resultDiv.style.display = "block";

    try {
        const response = await fetch("/api/analyze", {
            method: "POST",
            body: formData
        });

        if (!response.ok) {
            const err = await response.json();
            resultDiv.className = "show-result result-info";
            resultDiv.innerHTML = `Error: ${err.reason || err.result || response.statusText}`;
            return;
        }

        const data = await response.json();
        if (data.result) {
            // Detect verdict and adjust styling classes
            let verdictLabel = "";
            let verdictClass = "";
            if (/fake/i.test(data.result)) {
                verdictLabel = `<span class="result-label result-fake">❌ Fake Review</span>`;
                verdictClass = "show-result result-fake";
            } else if (/genuine|real/i.test(data.result)) {
                verdictLabel = `<span class="result-label result-genuine">✅ Genuine Review</span>`;
                verdictClass = "show-result result-genuine";
            } else {
                verdictLabel = `<span class="result-label result-info">ℹ️ ${data.result}</span>`;
                verdictClass = "show-result result-info";
            }

            // Try to get confidence value (default to data.reason or fallback)
            let confidence = "";
            let confidencePercent = "";
            // Check for a confidence value (as percent or float)
            if (typeof data.confidence !== "undefined") {
                confidencePercent = Number(data.confidence) * 100;
            } else {
                // fallback: try to extract percentage from reason
                const match = String(data.reason).match(/(\d+(\.\d+)?)%/);
                if (match) confidencePercent = match[1];
            }
            // Final fallback: default to empty
            if (confidencePercent) {
                confidence = `<div class="confidence-label">Model confidence: ${Number(confidencePercent).toFixed(2)}%</div>
                              <div class="confidence-bar">
                                <div class="confidence-progress" style="width:${confidencePercent}%"></div>
                              </div>`;
            }

            resultDiv.className = verdictClass;
            resultDiv.innerHTML = `
                ${verdictLabel}
                ${confidence}
            `;
        } else {
            resultDiv.className = "show-result result-info";
            resultDiv.innerHTML = "No result received.";
        }
    } catch (error) {
        resultDiv.className = "show-result result-info";
        resultDiv.innerHTML = "Error contacting backend.";
        console.error(error);
    }
});
