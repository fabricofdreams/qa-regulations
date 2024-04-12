import unittest
from unittest.mock import patch
import app


class TestMainApp(unittest.TestCase):
    @patch('main.prepare_data')  # Mock the prepare_data function
    # Mock the Streamlit button in the sidebar
    @patch('streamlit.sidebar.button')
    def test_prepare_data_button(self, mock_button, mock_prepare_data):
        # Simulate button click
        mock_button.return_value = True  # Simulate the button being clicked

        # Run the app function to test the button click handling
        app.run_chat()  # Assuming this is where your button click is handled

        # Check if prepare_data was called as a result
        mock_prepare_data.assert_called_once()


if __name__ == '__main__':
    unittest.main()
