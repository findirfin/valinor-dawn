import json
import requests
import os

def fetch_weather():
    # Replace with your actual weather API endpoint and parameters
    api_url = "https://api.weatherapi.com/v1/current.json?key=YOUR_API_KEY&q=YOUR_LOCATION"
    response = requests.get(api_url)
    if response.status_code == 200:
        return response.json()
    else:
        print("Failed to fetch weather data")
        return None

def fetch_news():
    # Replace with your actual news API endpoint and parameters
    api_url = "https://newsapi.org/v2/top-headlines?country=YOUR_COUNTRY&apiKey=YOUR_API_KEY"
    response = requests.get(api_url)
    if response.status_code == 200:
        return response.json()
    else:
        print("Failed to fetch news data")
        return None

def update_cache():
    weather_data = fetch_weather()
    news_data = fetch_news()

    if weather_data:
        with open(os.path.join('cache', 'weather.json'), 'w') as weather_file:
            json.dump(weather_data, weather_file)

    if news_data:
        with open(os.path.join('cache', 'news.json'), 'w') as news_file:
            json.dump(news_data, news_file)

if __name__ == "__main__":
    update_cache()