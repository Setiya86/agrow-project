$(document).ready(function() {
    const panenData = {{ panen_data|tojson }};
    const jualData = {{ jual_data|tojson }};
    const historyData = {{ history_data|tojson }};

    if (panenData.length === 0 && jualData.length === 0) {
        $('#chart-section').hide();
        $('#no-data-section').show();
    } else {
        $('#chart-section').show();
        $('#no-data-section').hide();

        const lineChartPanenLabels = panenData.map(entry => new Date(entry.tanggal_panen).toLocaleDateString());
        const lineChartPanenData = panenData.map(entry => entry.jumlah_panen);

        const lineChartJualLabels = jualData.map(entry => new Date(entry.tanggal_panen).toLocaleDateString());
        const lineChartJualData = jualData.map(entry => entry.jumlah_dijual);

        const lineCtxPanen = document.getElementById('lineChartPanen').getContext('2d');
        new Chart(lineCtxPanen, {
            type: 'line',
            data: {
                labels: lineChartPanenLabels,
                datasets: [{
                    label: 'Jumlah Panen (kg)',
                    data: lineChartPanenData,
                    backgroundColor: 'rgba(54, 162, 235, 0.2)',
                    borderColor: 'rgba(54, 162, 235, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });

        const lineCtxJual = document.getElementById('lineChartJual').getContext('2d');
        new Chart(lineCtxJual, {
            type: 'line',
            data: {
                labels: lineChartJualLabels,
                datasets: [{
                    label: 'Jumlah Dijual (kg)',
                    data: lineChartJualData,
                    backgroundColor: 'rgba(255, 206, 86, 0.2)',
                    borderColor: 'rgba(255, 206, 86, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });

        const totalPanen = lineChartPanenData.reduce((a, b) => a + b, 0);
        const totalJual = lineChartJualData.reduce((a, b) => a + b, 0);
        const pieCtx = document.getElementById('pieChart').getContext('2d');
        new Chart(pieCtx, {
            type: 'pie',
            data: {
                labels: ['Jumlah Panen', 'Jumlah Dijual'],
                datasets: [{
                    label: 'Persentase',
                    data: [totalPanen, totalJual],
                    backgroundColor: [
                        'rgba(54, 162, 235, 0.2)',
                        'rgba(255, 206, 86, 0.2)'
                    ],
                    borderColor: [
                        'rgba(54, 162, 235, 1)',
                        'rgba(255, 206, 86, 1)'
                    ],
                    borderWidth: 1
                }]
            }});
    }

    historyData.forEach(entry => {
        const ctx = document.getElementById(`barChart-${entry._id}`).getContext('2d');
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['Jumlah Panen', 'Jumlah Dijual'],
                datasets: [{
                    label: entry.commodity,
                    data: [entry.jumlah_panen, entry.jumlah_dijual],
                    backgroundColor: [
                        'rgba(54, 162, 235, 0.2)',
                        'rgba(255, 206, 86, 0.2)'
                    ],
                    borderColor: [
                        'rgba(54, 162, 235, 1)',
                        'rgba(255, 206, 86, 1)'
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    });
});

function showSection(section) {
    if (section === 'catatan') {
        $('#catatan-section').show();
        $('#aktivitas-section').hide();
    } else if (section === 'aktivitas') {
        $('#catatan-section').hide();
        $('#aktivitas-section').show();
    }
}

function editData(id, tanggal_panen, jumlah_dijual, jumlah_panen, harga_jual, commodity) {
    $('#edit-doc-id').val(id);
    $('#edit-tanggal_panen').val(tanggal_panen);
    $('#edit-jumlah_dijual').val(jumlah_dijual);
    $('#edit-jumlah_panen').val(jumlah_panen);
    $('#edit-harga_jual').val(harga_jual);
    $('#edit-commodity').val(commodity);
    $('#editDataModal').modal('show');
}
