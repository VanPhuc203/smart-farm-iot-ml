// plant-selection.js
document.addEventListener('DOMContentLoaded', function() {
    const plantSelect = document.getElementById('plant-select');
    const plantImage = document.querySelector('.plant-image');
    const applyButton = document.querySelector('.apply-button');
    const resultBox = document.querySelector('.result-box');
    const plantParameters = document.getElementById('plant-parameters');
    const recommendations = document.getElementById('recommendations');
    const recommendationList = document.getElementById('recommendation-list');
    const loadingSpinner = document.querySelector('.loading-spinner');

    if (resultBox) {
        resultBox.classList.add('hidden');
    }

    const plantImages = {
        'rice': '../static/img/plants/rice.webp',
        'maize': '../static/img/plants/maize.jpg',
        'chickpea': '../static/img/plants/chickpea.jpg',
        'kidneybeans': '../static/img/plants/kidneybeans.webp',
        'pigeonpeas': '../static/img/plants/pigeonpeas.jpg',
        'mothbeans': '../static/img/plants/mothbeans.webp',
        'mungbean': '../static/img/plants/mungbean.jpg',
        'blackgram': '../static/img/plants/blackgram.webp',
        'lentil': '../static/img/plants/lentil.jpg',
        'pomegranate': '../static/img/plants/pomegranate.jpeg',
        'banana': '../static/img/plants/banana.jpg',
        'mango': '../static/img/plants/mango.jpg',
        'grapes': '../static/img/plants/grapes.jpeg',
        'watermelon': '../static/img/plants/watermelon.jpeg',
        'muskmelon': '../static/img/plants/muskmelon.jpg',
        'apple': '../static/img/plants/apple.jpeg',
        'orange': '../static/img/plants/orange.jpg',
        'papaya': '../static/img/plants/papaya.jpg',
        'coconut': '../static/img/plants/coconut.jpeg',
        'cotton': '../static/img/plants/cotton.jpg',
        'jute': '../static/img/plants/jute.jpg',
        'coffee': '../static/img/plants/coffee.jpeg'
    };

    const plantIdealParameters = {
        'rice': {
            'temperature': {'min': 20, 'max': 27, 'ideal': 24},
            'humidity': {'min': 80, 'max': 85, 'ideal': 82},
            'ph': {'min': 5.0, 'max': 7.8, 'ideal': 6.4},
            'nitrogen': {'min': 60, 'max': 99, 'ideal': 80},
            'phosphorus': {'min': 35, 'max': 60, 'ideal': 48},
            'potassium': {'min': 35, 'max': 45, 'ideal': 40}
        },
        'maize': {
            'temperature': {'min': 18, 'max': 26, 'ideal': 22},
            'humidity': {'min': 55, 'max': 74, 'ideal': 64},
            'ph': {'min': 5.5, 'max': 7.0, 'ideal': 6.2},
            'nitrogen': {'min': 60, 'max': 100, 'ideal': 80},
            'phosphorus': {'min': 35, 'max': 60, 'ideal': 48},
            'potassium': {'min': 15, 'max': 25, 'ideal': 20}
        },
        'chickpea': {
            'temperature': {'min': 17, 'max': 21, 'ideal': 19},
            'humidity': {'min': 14, 'max': 20, 'ideal': 17},
            'ph': {'min': 6.0, 'max': 8.9, 'ideal': 7.5},
            'nitrogen': {'min': 20, 'max': 60, 'ideal': 40},
            'phosphorus': {'min': 55, 'max': 80, 'ideal': 68},
            'potassium': {'min': 75, 'max': 85, 'ideal': 80}
        },
        'kidneybeans': {
            'temperature': {'min': 15, 'max': 24, 'ideal': 20},
            'humidity': {'min': 18, 'max': 25, 'ideal': 22},
            'ph': {'min': 5.5, 'max': 6.0, 'ideal': 5.8},
            'nitrogen': {'min': 0, 'max': 40, 'ideal': 20},
            'phosphorus': {'min': 55, 'max': 80, 'ideal': 68},
            'potassium': {'min': 15, 'max': 25, 'ideal': 20}
        },
        'pigeonpeas': {
            'temperature': {'min': 18, 'max': 39, 'ideal': 28},
            'humidity': {'min': 14, 'max': 35, 'ideal': 24},
            'ph': {'min': 4.0, 'max': 8.8, 'ideal': 6.4},
            'nitrogen': {'min': 0, 'max': 40, 'ideal': 20},
            'phosphorus': {'min': 55, 'max': 80, 'ideal': 68},
            'potassium': {'min': 15, 'max': 25, 'ideal': 20}
        },
        'mothbeans': {
            'temperature': {'min': 24, 'max': 32, 'ideal': 28},
            'humidity': {'min': 25, 'max': 35, 'ideal': 30},
            'ph': {'min': 3.5, 'max': 9.0, 'ideal': 6.2},
            'nitrogen': {'min': 0, 'max': 40, 'ideal': 20},
            'phosphorus': {'min': 35, 'max': 60, 'ideal': 48},
            'potassium': {'min': 15, 'max': 25, 'ideal': 20}
        },
        'mungbean': {
            'temperature': {'min': 27, 'max': 30, 'ideal': 28},
            'humidity': {'min': 80, 'max': 90, 'ideal': 85},
            'ph': {'min': 6.2, 'max': 7.6, 'ideal': 6.9},
            'nitrogen': {'min': 0, 'max': 40, 'ideal': 20},
            'phosphorus': {'min': 35, 'max': 60, 'ideal': 48},
            'potassium': {'min': 15, 'max': 25, 'ideal': 20}
        },
        'blackgram': {
            'temperature': {'min': 26, 'max': 32, 'ideal': 29},
            'humidity': {'min': 60, 'max': 70, 'ideal': 65},
            'ph': {'min': 4.9, 'max': 7.6, 'ideal': 6.2},
            'nitrogen': {'min': 0, 'max': 40, 'ideal': 20},
            'phosphorus': {'min': 55, 'max': 80, 'ideal': 68},
            'potassium': {'min': 15, 'max': 25, 'ideal': 20}
        },
        'lentil': {
            'temperature': {'min': 18, 'max': 27, 'ideal': 22},
            'humidity': {'min': 60, 'max': 70, 'ideal': 65},
            'ph': {'min': 5.8, 'max': 7.8, 'ideal': 6.8},
            'nitrogen': {'min': 0, 'max': 40, 'ideal': 20},
            'phosphorus': {'min': 55, 'max': 80, 'ideal': 68},
            'potassium': {'min': 15, 'max': 25, 'ideal': 20}
        },
        'pomegranate': {
            'temperature': {'min': 18, 'max': 24, 'ideal': 21},
            'humidity': {'min': 85, 'max': 95, 'ideal': 90},
            'ph': {'min': 5.4, 'max': 7.8, 'ideal': 6.6},
            'nitrogen': {'min': 0, 'max': 40, 'ideal': 20},
            'phosphorus': {'min': 5, 'max': 30, 'ideal': 18},
            'potassium': {'min': 35, 'max': 45, 'ideal': 40}
        },
        'banana': {
            'temperature': {'min': 25, 'max': 30, 'ideal': 28},
            'humidity': {'min': 75, 'max': 85, 'ideal': 80},
            'ph': {'min': 5.0, 'max': 7.0, 'ideal': 6.0},
            'nitrogen': {'min': 80, 'max': 120, 'ideal': 100},
            'phosphorus': {'min': 5, 'max': 30, 'ideal': 18},
            'potassium': {'min': 45, 'max': 55, 'ideal': 50}
        },
        'mango': {
            'temperature': {'min': 27, 'max': 35, 'ideal': 31},
            'humidity': {'min': 45, 'max': 55, 'ideal': 50},
            'ph': {'min': 4.3, 'max': 7.6, 'ideal': 6.0},
            'nitrogen': {'min': 0, 'max': 40, 'ideal': 20},
            'phosphorus': {'min': 15, 'max': 40, 'ideal': 28},
            'potassium': {'min': 25, 'max': 35, 'ideal': 30}
        },
        'grapes': {
            'temperature': {'min': 8, 'max': 32, 'ideal': 20},
            'humidity': {'min': 80, 'max': 85, 'ideal': 82},
            'ph': {'min': 5.5, 'max': 7.0, 'ideal': 6.2},
            'nitrogen': {'min': 0, 'max': 40, 'ideal': 20},
            'phosphorus': {'min': 120, 'max': 145, 'ideal': 132},
            'potassium': {'min': 195, 'max': 205, 'ideal': 200}
        },
        'watermelon': {
            'temperature': {'min': 24, 'max': 27, 'ideal': 26},
            'humidity': {'min': 80, 'max': 90, 'ideal': 85},
            'ph': {'min': 6.0, 'max': 6.8, 'ideal': 6.4},
            'nitrogen': {'min': 80, 'max': 120, 'ideal': 100},
            'phosphorus': {'min': 5, 'max': 30, 'ideal': 18},
            'potassium': {'min': 5, 'max': 15, 'ideal': 10}
        },
        'muskmelon': {
            'temperature': {'min': 27, 'max': 29, 'ideal': 28},
            'humidity': {'min': 90, 'max': 95, 'ideal': 92},
            'ph': {'min': 6.0, 'max': 6.8, 'ideal': 6.4},
            'nitrogen': {'min': 80, 'max': 120, 'ideal': 100},
            'phosphorus': {'min': 5, 'max': 30, 'ideal': 18},
            'potassium': {'min': 5, 'max': 15, 'ideal': 10}
        },
        'apple': {
            'temperature': {'min': 21, 'max': 24, 'ideal': 22},
            'humidity': {'min': 85, 'max': 95, 'ideal': 90},
            'ph': {'min': 5.5, 'max': 7.0, 'ideal': 6.2},
            'nitrogen': {'min': 0, 'max': 40, 'ideal': 20},
            'phosphorus': {'min': 120, 'max': 145, 'ideal': 132},
            'potassium': {'min': 195, 'max': 205, 'ideal': 200}
        },
        'orange': {
            'temperature': {'min': 10, 'max': 34, 'ideal': 22},
            'humidity': {'min': 85, 'max': 95, 'ideal': 90},
            'ph': {'min': 4.0, 'max': 9.0, 'ideal': 6.5},
            'nitrogen': {'min': 0, 'max': 40, 'ideal': 20},
            'phosphorus': {'min': 5, 'max': 30, 'ideal': 18},
            'potassium': {'min': 5, 'max': 15, 'ideal': 10}
        },
        'papaya': {
            'temperature': {'min': 23, 'max': 44, 'ideal': 34},
            'humidity': {'min': 85, 'max': 95, 'ideal': 90},
            'ph': {'min': 4.3, 'max': 7.6, 'ideal': 6.0},
            'nitrogen': {'min': 40, 'max': 80, 'ideal': 60},
            'phosphorus': {'min': 5, 'max': 60, 'ideal': 32},
            'potassium': {'min': 45, 'max': 55, 'ideal': 50}
        },
        'coconut': {
            'temperature': {'min': 25, 'max': 30, 'ideal': 28},
            'humidity': {'min': 90, 'max': 100, 'ideal': 95},
            'ph': {'min': 5.5, 'max': 6.5, 'ideal': 6.0},
            'nitrogen': {'min': 0, 'max': 40, 'ideal': 20},
            'phosphorus': {'min': 5, 'max': 30, 'ideal': 18},
            'potassium': {'min': 25, 'max': 35, 'ideal': 30}
        },
        'cotton': {
            'temperature': {'min': 22, 'max': 26, 'ideal': 24},
            'humidity': {'min': 75, 'max': 85, 'ideal': 80},
            'ph': {'min': 5.8, 'max': 8.0, 'ideal': 6.9},
            'nitrogen': {'min': 100, 'max': 140, 'ideal': 120},
            'phosphorus': {'min': 35, 'max': 60, 'ideal': 48},
            'potassium': {'min': 15, 'max': 25, 'ideal': 20}
        },
        'jute': {
            'temperature': {'min': 23, 'max': 27, 'ideal': 25},
            'humidity': {'min': 70, 'max': 90, 'ideal': 80},
            'ph': {'min': 6.0, 'max': 7.5, 'ideal': 6.8},
            'nitrogen': {'min': 60, 'max': 100, 'ideal': 80},
            'phosphorus': {'min': 35, 'max': 60, 'ideal': 48},
            'potassium': {'min': 35, 'max': 45, 'ideal': 40}
        },
        'coffee': {
            'temperature': {'min': 23, 'max': 28, 'ideal': 26},
            'humidity': {'min': 50, 'max': 70, 'ideal': 60},
            'ph': {'min': 6.0, 'max': 7.5, 'ideal': 6.8},
            'nitrogen': {'min': 80, 'max': 120, 'ideal': 100},
            'phosphorus': {'min': 15, 'max': 40, 'ideal': 28},
            'potassium': {'min': 25, 'max': 35, 'ideal': 30}
        }
    };

    function getBaseUrl() {
        return window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
            ? 'http://localhost:8000'
            : `${window.location.protocol}//${window.location.host}`;
    }

    async function getCurrentSoilData() {
        try {
            const response = await fetch(`${getBaseUrl()}/latest-data`);
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            const data = await response.json();
            return {
                temperature: data.temperature || 25,
                humidity: data.humidity || 65,
                ph: data.ph || 6.5,
                nitrogen: data.nitrogen || 85,
                phosphorus: data.phosphorus || 25,
                potassium: data.potassium || 35
            };
        } catch (error) {
            console.error('Error fetching current soil data:', error);
            return {
                temperature: 25,
                humidity: 65,
                ph: 6.5,
                nitrogen: 85,
                phosphorus: 25,
                potassium: 35
            };
        }
    }

    function updatePlantImage(selectedPlant) {
        if (!plantImage || !loadingSpinner) {
            console.warn('Không tìm thấy các element cần thiết');
            return;
        }

        const imagePath = plantImages[selectedPlant] || '../static/img/plants/default-plant.jpg';

        plantImage.classList.add('loading');
        loadingSpinner.classList.add('active');

        const img = new Image();
        
        img.onload = function() {
            plantImage.src = imagePath;
            plantImage.alt = `Hình ảnh ${selectedPlant}`;

            setTimeout(() => {
                plantImage.classList.remove('loading');
                loadingSpinner.classList.remove('active');
            }, 300);
        };

        img.onerror = function() {
            console.warn(`Không thể tải ảnh cho ${selectedPlant}, sử dụng ảnh mặc định`);
            plantImage.src = '../static/img/plants/default-plant.jpg';
            plantImage.alt = 'Hình ảnh mặc định';

            plantImage.classList.remove('loading');
            loadingSpinner.classList.remove('active');
        };

        img.src = imagePath;
    }

    function updateParameterDisplay(currentData, idealParams) {
        const parameters = ['temp', 'humidity', 'ph', 'n', 'p', 'k'];
        const cards = document.querySelectorAll('.parameter-card');

        plantParameters.classList.remove('hidden');

        cards.forEach(card => card.classList.add('hide'));

        setTimeout(() => {
            parameters.forEach((param, index) => {
                const currentElement = document.getElementById(`${param}-current`);
                const idealElement = document.getElementById(`${param}-ideal`);
                
                if (!currentElement || !idealElement) return;

                let currentValue, idealValue;
                
                switch(param) {
                    case 'temp':
                        currentValue = currentData.temperature;
                        idealValue = idealParams.temperature.ideal;
                        break;
                    case 'humidity':
                        currentValue = currentData.humidity;
                        idealValue = idealParams.humidity.ideal;
                        break;
                    case 'ph':
                        currentValue = currentData.ph;
                        idealValue = idealParams.ph.ideal;
                        break;
                    case 'n':
                        currentValue = currentData.nitrogen;
                        idealValue = idealParams.nitrogen.ideal;
                        break;
                    case 'p':
                        currentValue = currentData.phosphorus;
                        idealValue = idealParams.phosphorus.ideal;
                        break;
                    case 'k':
                        currentValue = currentData.potassium;
                        idealValue = idealParams.potassium.ideal;
                        break;
                }

                const oldValue = currentElement.textContent;
                const newValue = currentValue.toFixed(1);
                
                if (oldValue !== newValue) {
                    currentElement.classList.add('changed');
                    setTimeout(() => currentElement.classList.remove('changed'), 1000);
                }
                currentElement.textContent = newValue;

                idealElement.textContent = idealValue.toFixed(1);

                setTimeout(() => {
                    cards[index].classList.remove('hide');
                    cards[index].classList.add('show');
                }, index * 100);
            });
        }, 300);
    }

    function generateRecommendations(currentData, idealParams) {
        const recommendations = [];

        if (currentData.temperature < idealParams.temperature.min) {
            recommendations.push(`Nhiệt độ hiện tại (${currentData.temperature.toFixed(1)}°C) thấp hơn mức tối thiểu (${idealParams.temperature.min}°C). Cần tăng nhiệt độ.`);
        } else if (currentData.temperature > idealParams.temperature.max) {
            recommendations.push(`Nhiệt độ hiện tại (${currentData.temperature.toFixed(1)}°C) cao hơn mức tối đa (${idealParams.temperature.max}°C). Cần giảm nhiệt độ.`);
        }

        if (currentData.humidity < idealParams.humidity.min) {
            recommendations.push(`Độ ẩm hiện tại (${currentData.humidity.toFixed(1)}%) thấp hơn mức tối thiểu (${idealParams.humidity.min}%). Cần tăng độ ẩm.`);
        } else if (currentData.humidity > idealParams.humidity.max) {
            recommendations.push(`Độ ẩm hiện tại (${currentData.humidity.toFixed(1)}%) cao hơn mức tối đa (${idealParams.humidity.max}%). Cần giảm độ ẩm.`);
        }

        if (currentData.ph < idealParams.ph.min) {
            recommendations.push(`pH hiện tại (${currentData.ph.toFixed(1)}) thấp hơn mức tối thiểu (${idealParams.ph.min}). Cần tăng pH.`);
        } else if (currentData.ph > idealParams.ph.max) {
            recommendations.push(`pH hiện tại (${currentData.ph.toFixed(1)}) cao hơn mức tối đa (${idealParams.ph.max}). Cần giảm pH.`);
        }

        if (currentData.nitrogen < idealParams.nitrogen.min) {
            recommendations.push(`Nitrogen hiện tại (${currentData.nitrogen.toFixed(1)} mg/kg) thấp hơn mức tối thiểu (${idealParams.nitrogen.min} mg/kg). Cần bổ sung phân đạm.`);
        } else if (currentData.nitrogen > idealParams.nitrogen.max) {
            recommendations.push(`Nitrogen hiện tại (${currentData.nitrogen.toFixed(1)} mg/kg) cao hơn mức tối đa (${idealParams.nitrogen.max} mg/kg). Cần giảm bón phân đạm.`);
        }

        if (currentData.phosphorus < idealParams.phosphorus.min) {
            recommendations.push(`Phosphorus hiện tại (${currentData.phosphorus.toFixed(1)} mg/kg) thấp hơn mức tối thiểu (${idealParams.phosphorus.min} mg/kg). Cần bổ sung phân lân.`);
        } else if (currentData.phosphorus > idealParams.phosphorus.max) {
            recommendations.push(`Phosphorus hiện tại (${currentData.phosphorus.toFixed(1)} mg/kg) cao hơn mức tối đa (${idealParams.phosphorus.max} mg/kg). Cần giảm bón phân lân.`);
        }

        if (currentData.potassium < idealParams.potassium.min) {
            recommendations.push(`Potassium hiện tại (${currentData.potassium.toFixed(1)} mg/kg) thấp hơn mức tối thiểu (${idealParams.potassium.min} mg/kg). Cần bổ sung phân kali.`);
        } else if (currentData.potassium > idealParams.potassium.max) {
            recommendations.push(`Potassium hiện tại (${currentData.potassium.toFixed(1)} mg/kg) cao hơn mức tối đa (${idealParams.potassium.max} mg/kg). Cần giảm bón phân kali.`);
        }

        return recommendations;
    }

    function updateRecommendations(recommendations) {
        const recommendationList = document.getElementById('recommendation-list');
        recommendationList.innerHTML = '';
        
        recommendations.forEach((rec, index) => {
            const li = document.createElement('li');
            li.className = 'recommendation-item';
            li.textContent = rec;
            
            setTimeout(() => {
                li.classList.add('show');
            }, index * 100);
            
            recommendationList.appendChild(li);
        });

        document.getElementById('recommendations').classList.remove('hidden');
    }

    function updateResultBox(message) {
        if (resultBox) {
            resultBox.textContent = message;
            resultBox.classList.add('highlight');
            setTimeout(() => {
                resultBox.classList.remove('highlight');
            }, 1000);
        }
    }

    function checkParameterWarnings(currentData, idealParams) {
        return {
            temperature: currentData.temperature < idealParams.temperature.min || currentData.temperature > idealParams.temperature.max,
            humidity: currentData.humidity < idealParams.humidity.min || currentData.humidity > idealParams.humidity.max,
            ph: currentData.ph < idealParams.ph.min || currentData.ph > idealParams.ph.max,
            nitrogen: currentData.nitrogen < idealParams.nitrogen.min || currentData.nitrogen > idealParams.nitrogen.max,
            phosphorus: currentData.phosphorus < idealParams.phosphorus.min || currentData.phosphorus > idealParams.phosphorus.max,
            potassium: currentData.potassium < idealParams.potassium.min || currentData.potassium > idealParams.potassium.max
        };
    }

    applyButton.addEventListener('click', async function() {
        const selectedPlant = plantSelect.value;
        
        if (!selectedPlant) {
            alert('Vui lòng chọn loại cây trước khi áp dụng!');
            return;
        }

        try {
            const currentData = await getCurrentSoilData();
            
            const idealParams = plantIdealParameters[selectedPlant];

            if (!idealParams) {
                throw new Error('Không tìm thấy thông số lý tưởng cho loại cây này');
            }

            const warnings = checkParameterWarnings(currentData, idealParams);

            saveToLocalStorage({
                selectedPlant,
                parameters: {
                    current: currentData,
                    ideal: idealParams,
                    warnings: warnings
                },
                recommendations: generateRecommendations(currentData, idealParams)
            });

            updateParameterDisplay(currentData, idealParams);

            const recommendations = generateRecommendations(currentData, idealParams);
            updateRecommendations(recommendations);

            resultBox.classList.remove('hidden');
            updateResultBox('Bây giờ chúng tôi sẽ theo dõi và đề xuất cải thiện chất lượng đất để phù hợp với cây trồng của bạn.');

        } catch (error) {
            console.error('Lỗi khi cập nhật thông số:', error);
            alert('Có lỗi xảy ra khi cập nhật thông số. Vui lòng thử lại sau.');
        }
    });

    plantSelect.addEventListener('change', function() {
        const selectedPlant = this.value;
        updatePlantImage(selectedPlant);
    });

    function saveToLocalStorage(data) {
        localStorage.setItem('plantSelectionData', JSON.stringify(data));
    }

    function getFromLocalStorage() {
        const data = localStorage.getItem('plantSelectionData');
        return data ? JSON.parse(data) : null;
    }

    function updateUIFromSavedData(data) {
        if (!data) return;

        plantSelect.value = data.selectedPlant;

        if (data.selectedPlant) {
            updatePlantImage(data.selectedPlant);
        }

        if (data.parameters) {
            updateParameterDisplay(data.parameters.current, data.parameters.ideal);
            plantParameters.classList.remove('hidden');
        }

        if (data.recommendations) {
            updateRecommendations(data.recommendations);
            recommendations.classList.remove('hidden');
        }

        if (data.selectedPlant) {
            resultBox.classList.remove('hidden');
        }
    }

    const savedData = getFromLocalStorage();
    if (savedData) {
        updateUIFromSavedData(savedData);
    }
});