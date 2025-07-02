# Weather Assistant - AI-Powered Weather Advisor

A Flask web application that integrates with MCP (Model Context Protocol) weather server to provide intelligent weather advice and recommendations.

## Features

- 🌤️ Real-time weather information
- 🌡️ Air quality index monitoring
- 💬 Interactive chat interface
- 🤖 AI-powered recommendations for outdoor activities
- 🧹 Chat history management
- 📱 Responsive design

## Prerequisites

Before running this application, you need:

1. **GitHub Token**: Create a personal access token (PAT) in your GitHub settings
   - Follow instructions: [Managing Personal Access Tokens](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens)
   - Set the token as an environment variable: `GITHUB_TOKEN`

2. **MCP Weather Server**: You need to have the MCP weather server installed and running
   - Update the path in `app.py` to point to your MCP weather server location

## Installation

1. Clone this repository:
   ```bash
   git clone <repository-url>
   cd starter-project
   ```

2. Install the required dependencies:
   ```bash
   pip install flask flask-cors mcp openai
   ```

3. Set up your environment variables:
   ```bash
   set GITHUB_TOKEN=your_github_token_here
   ```

4. Update the MCP server path in `app.py`:
   ```python
   # Update this path to your MCP weather server location
   "C:\\Users\\sharonxu\\mcp-weather-server\\dist\\index.js"
   ```

## Usage

1. Start the Flask application:
   ```bash
   python app.py
   ```

2. Open your web browser and navigate to:
   ```
   http://localhost:5000
   ```

3. Start chatting with the weather assistant! You can ask questions like:
   - "What's the weather like today?"
   - "Should I go for a run?"
   - "What should I wear outside?"
   - "Is the air quality good for outdoor activities?"

## API Endpoints

- `POST /api/send_message` - Send a message to the AI assistant
- `GET /api/weather` - Get weather information for a specific city
- `GET /api/model_response` - Get the latest model response
- `GET /api/message_history` - Get complete conversation history
- `POST /api/clear_history` - Clear conversation history

## Project Structure

```
starter-project/
├── app.py              # Main Flask application
├── requirements.txt    # Python dependencies
├── test2.py           # Additional test file
├── static/
│   ├── script.js      # Frontend JavaScript
│   └── styles.css     # CSS styles
└── templates/
    └── index.html     # Main HTML template
```

## Technologies Used

- **Backend**: Flask, Python
- **Frontend**: HTML, CSS, JavaScript
- **AI Integration**: OpenAI API via Azure AI
- **Protocol**: Model Context Protocol (MCP)
- **Styling**: Modern CSS with blue theme

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is open source and available under the [MIT License](LICENSE).

## Support

If you encounter any issues or have questions, please create an issue in this repository.
