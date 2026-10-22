const API_URL = '/graphql';
const API_TOKEN = 'student_civilian_token'; 

async function graphqlCall(queryStr, variables = {}) {
    const response = await fetch(API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${API_TOKEN}` },
        body: JSON.stringify({ query: queryStr, variables: variables })
    });
    const result = await response.json();
    if (result.errors) throw new Error(result.errors[0].message);
    return result.data;
}

async function loadDashboard() {
    const query = `query { me { username, mySatellites { id designation } } }`;
    try {
        const data = await graphqlCall(query);
        document.getElementById('user-name').innerText = data.me.username;
        
        const list = document.getElementById('my-sat-list');
        list.innerHTML = '';
        if (data.me.mySatellites.length === 0) {
            list.innerHTML = '<tr><td colspan="3" style="color: #64748b; text-align:center;">No assets deployed.</td></tr>';
        } else {
            data.me.mySatellites.forEach(sat => {
                list.innerHTML += `<tr>
                    <td>${sat.id}</td>
                    <td>${sat.designation}</td>
                    <td><span class="success-text">Online</span></td>
                </tr>`;
            });
        }
    } catch (e) {
        console.error("Failed to load dashboard:", e);
    }
}

window.viewData = async function(targetId) {
    const output = document.getElementById('telemetry-output');
    output.innerHTML = 'Establishing secure link...';
    
    const query = `
        query GetSatData($id: ID!) {
            satelliteInfo(id: $id) {
                telemetryData { sensorType rawData }
            }
        }
    `;

    try {
        const data = await graphqlCall(query, { id: targetId });
        if (data.satelliteInfo && data.satelliteInfo.telemetryData) {
            let text = `--- DOWNLINK ESTABLISHED ---
`;
            data.satelliteInfo.telemetryData.forEach(t => {
                text += `[${t.sensorType}]: ${t.rawData}
`;
            });
            output.innerHTML = `<span class="success-text">${text}</span>`;
        }
    } catch (e) {
        output.innerHTML = `<span class="error-text">CONNECTION TERMINATED
${e.message}</span>`;
    }
}

document.getElementById('btn-launch').addEventListener('click', async () => {
    const designation = document.getElementById('sat-name').value || "CIVILIAN-PROBE-1";
    const mutation = `mutation { launchCubeSat(designation: "${designation}") { id } }`;
    
    try {
        await graphqlCall(mutation);
        document.getElementById('sat-name').value = '';
        loadDashboard();
    } catch (e) {
        alert("Launch failed: " + e.message);
    }
});

document.getElementById('btn-refresh').addEventListener('click', loadDashboard);
window.addEventListener('DOMContentLoaded', loadDashboard);
