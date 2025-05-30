# web_bg_remover.py
import os
from flask import Flask, request, render_template_string, send_file, jsonify
from PIL import Image
from rembg import remove
import io
import uuid # For unique filenames
import logging
import webbrowser
import threading
import time
import socket

# Configure logging
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
PROCESSED_FOLDER = 'processed'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

# --- HTML Template with Tailwind CSS and JavaScript for Drag & Drop ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Background Remover</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { font-family: 'Inter', sans-serif; }
        .drop-zone {
            border: 2px dashed #ccc;
            border-radius: 0.5rem;
            padding: 2rem;
            text-align: center;
            transition: background-color 0.2s ease-in-out, border-color 0.2s ease-in-out;
        }
        .drop-zone.dragover {
            background-color: #e9e9e9;
            border-color: #aaa;
        }
        .spinner {
            border: 4px solid rgba(0, 0, 0, 0.1);
            width: 36px;
            height: 36px;
            border-radius: 50%;
            border-left-color: #09f;
            animation: spin 1s ease infinite;
            margin: 1rem auto;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .hidden { display: none; }
        img { max-width: 100%; height: auto; border-radius: 0.375rem; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    </style>
</head>
<body class="bg-gray-100 min-h-screen flex flex-col items-center justify-center p-4">

    <div class="bg-white p-6 sm:p-8 rounded-lg shadow-xl w-full max-w-lg">
        <h1 class="text-2xl sm:text-3xl font-bold text-center text-gray-700 mb-6">Image Background Remover</h1>

        <div id="dropZone" class="drop-zone mb-6 cursor-pointer">
            <p class="text-gray-500">Drag & drop an image here, or click to select</p>
            <input type="file" id="fileInput" class="hidden" accept="image/png, image/jpeg, image/gif, image/bmp, image/tiff">
        </div>
        
        <div id="errorMessage" class="text-red-500 text-center mb-4 hidden"></div>
        <div id="loadingSpinner" class="spinner hidden"></div>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 items-start">
            <div>
                <h2 class="text-lg font-semibold text-gray-600 mb-2 text-center sm:text-left">Original</h2>
                <img id="originalImage" src="https://placehold.co/300x200/e2e8f0/94a3b8?text=Original+Image" alt="Original Image" class="mx-auto sm:mx-0">
            </div>
            <div>
                <h2 class="text-lg font-semibold text-gray-600 mb-2 text-center sm:text-left">Processed</h2>
                <img id="processedImage" src="https://placehold.co/300x200/e2e8f0/94a3b8?text=Processed+Image" alt="Processed Image" class="mx-auto sm:mx-0">
            </div>
                <div class="sm:col-span-2">
                <a id="downloadLink" href="#" class="block mt-3 w-full text-center bg-blue-500 hover:bg-blue-600 text-white font-semibold py-2 px-4 rounded-md shadow-md transition duration-150 ease-in-out">
                Download Image
                </a>
  </div>
        </div>
         <p id="statusMessage" class="text-sm text-gray-500 text-center mt-4"></p>
    </div>

    <footer class="text-center text-gray-500 mt-8 text-sm">
        Made with ❤️ by Ryan
    </footer>

    <script>
        const dropZone = document.getElementById('dropZone');
        const fileInput = document.getElementById('fileInput');
        const originalImage = document.getElementById('originalImage');
        const processedImage = document.getElementById('processedImage');
        const downloadLink = document.getElementById('downloadLink');
        const loadingSpinner = document.getElementById('loadingSpinner');
        const errorMessage = document.getElementById('errorMessage');
        const statusMessage = document.getElementById('statusMessage');

        // Handle click on drop zone to trigger file input
        dropZone.addEventListener('click', () => fileInput.click());

        // Handle file selection via input
        fileInput.addEventListener('change', (e) => {
            const files = e.target.files;
            if (files.length > 0) {
                handleFile(files[0]);
            }
        });

        // Drag and Drop events
        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.classList.add('dragover');
        });

        dropZone.addEventListener('dragleave', () => {
            dropZone.classList.remove('dragover');
        });

        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('dragover');
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                handleFile(files[0]);
            }
        });

        async function handleFile(file) {
            if (!file.type.startsWith('image/')) {
                showError('Please upload an image file.');
                return;
            }

            // Display original image preview
            const reader = new FileReader();
            reader.onload = (e) => {
                originalImage.src = e.target.result;
            }
            reader.readAsDataURL(file);

            // Prepare form data for upload
            const formData = new FormData();
            formData.append('file', file);

            // Reset UI
            processedImage.src = 'https://placehold.co/300x200/e2e8f0/94a3b8?text=Processing...';
            downloadLink.classList.add('hidden');
            loadingSpinner.classList.remove('hidden');
            errorMessage.classList.add('hidden');
            statusMessage.textContent = 'Uploading and processing...';


            try {
                const response = await fetch('/upload', {
                    method: 'POST',
                    body: formData
                });

                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({ error: 'Server error occurred.' }));
                    throw new Error(errorData.error || `Server responded with ${response.status}`);
                }

                const result = await response.json();
                
                if (result.processed_image_url) {
                    // Add a cache-busting query parameter
                    processedImage.src = result.processed_image_url + '?t=' + new Date().getTime();
                    downloadLink.href = result.processed_image_url;
                    downloadLink.download = result.download_filename || 'background_removed.png';
                    downloadLink.classList.remove('hidden');
                    statusMessage.textContent = 'Processing complete!';
                } else if (result.error) {
                    showError(result.error);
                    statusMessage.textContent = 'Processing failed.';
                }
            } catch (error) {
                console.error('Upload error:', error);
                showError('Upload failed: ' + error.message);
                statusMessage.textContent = 'An error occurred.';
                processedImage.src = 'https://placehold.co/300x200/e2e8f0/94a3b8?text=Error';

            } finally {
                loadingSpinner.classList.add('hidden');
            }
        }
        
        function showError(message) {
            errorMessage.textContent = message;
            errorMessage.classList.remove('hidden');
            processedImage.src = 'https://placehold.co/300x200/e2e8f0/94a3b8?text=Error';
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """Serves the main HTML page."""
    return render_template_string(HTML_TEMPLATE)

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handles file upload, processes it, and returns the processed image URL."""
    if 'file' not in request.files:
        app.logger.error("No file part in request")
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        app.logger.error("No selected file")
        return jsonify({'error': 'No selected file'}), 400

    if file:
        try:
            filename = str(uuid.uuid4()) 
            original_ext = os.path.splitext(file.filename)[1].lower()
            if original_ext not in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff']:
                return jsonify({'error': 'Invalid file type. Please upload an image.'}), 400

            input_filename = filename + original_ext
            output_filename = filename + "_no_bg.png" 

            input_path = os.path.join(UPLOAD_FOLDER, input_filename)
            output_path = os.path.join(PROCESSED_FOLDER, output_filename)
            
            app.logger.info(f"Saving uploaded file to: {input_path}")
            file.save(input_path)

            app.logger.info(f"Opening image: {input_path}")
            input_image = Image.open(input_path)
            
            app.logger.info("Removing background...")
           
            output_image = remove(input_image)
            
            app.logger.info(f"Saving processed image to: {output_path}")
            output_image.save(output_path)

           
            try:
                os.remove(input_path)
                app.logger.info(f"Removed original uploaded file: {input_path}")
            except Exception as e:
                app.logger.error(f"Error removing original uploaded file {input_path}: {e}")


            return jsonify({
                'processed_image_url': f'/processed/{output_filename}',
                'download_filename': output_filename
            })

        except Exception as e:
            app.logger.error(f"Error processing file: {e}", exc_info=True)
            return jsonify({'error': f'An error occurred during processing: {str(e)}'}), 500
    
    return jsonify({'error': 'Unknown error'}), 500


@app.route('/processed/<filename>')
def send_processed_file(filename):
    """Serves the processed image."""
    file_path = os.path.join(PROCESSED_FOLDER, filename)
    if not os.path.exists(file_path):
        app.logger.error(f"Processed file not found: {file_path}")
        return "File not found", 404
    return send_file(file_path, mimetype='image/png')


def run_app():
    app.run(host='0.0.0.0', port=5000, debug=False)

def wait_for_server(host='localhost', port=5000, timeout=10):
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except OSError:
            time.sleep(0.1)
    return False

if __name__ == '__main__':
    flask_thread = threading.Thread(target=run_app)
    flask_thread.daemon = True
    flask_thread.start()

    if wait_for_server():
        webbrowser.open_new("http://localhost:5000/")
    else:
        print("Server did not start in time, not opening browser.")

    try:
        # Wait for Flask thread to finish (runs forever unless interrupted)
        flask_thread.join()
    except KeyboardInterrupt:
        print("\nServer shutting down cleanly.")
