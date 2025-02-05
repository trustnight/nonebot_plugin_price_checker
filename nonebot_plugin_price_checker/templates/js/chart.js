function renderChart(ctxId, data, type = 'line') {
    const ctx = document.getElementById(ctxId).getContext('2d');

    if (!data || !data.length) {
        return;
    }

    // 假设 data 是时间戳列表，我们将这些时间戳格式化为 24 小时制字符串
    const labels = data.map((item, index) => {
        const date = new Date(item); // 假设每个 item 是一个时间戳
        return date.toLocaleTimeString('en-GB', { hour12: false });  // 使用24小时制
    });

    new Chart(ctx, {
        type: type,
        data: {
            labels: labels,  // 使用格式化后的24小时制时间标签
            datasets: [{
                label: '最低价趋势',
                data: data,
                borderColor: '#3e95cd',
                backgroundColor: 'rgba(62, 149, 205, 0.2)',
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: {
                    beginAtZero: false,
                    grid: { color: '#eee' }
                },
                x: {
                    grid: { display: false }
                }
            }
        }
    });
}
