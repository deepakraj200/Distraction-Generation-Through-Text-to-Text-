from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_from_directory
import os
import json
import uuid
import requests
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__, static_folder='static')
app.secret_key = "your_secret_key"  # Replace with a strong secret key in production

# API Configuration
GSK_API_KEY = "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"
GSK_API_ENDPOINT = "https://api.generativeai.com/v1/generate"

# Folder structure
DATA_FOLDER = 'data'
TESTS_FOLDER = os.path.join(DATA_FOLDER, 'tests')
RESULTS_FOLDER = os.path.join(DATA_FOLDER, 'results')
MATERIALS_FOLDER = os.path.join(DATA_FOLDER, 'materials')

# Create necessary directories
os.makedirs(TESTS_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)
os.makedirs(MATERIALS_FOLDER, exist_ok=True)

# File upload configuration
ALLOWED_EXTENSIONS = {'pdf'}
app.config['UPLOAD_FOLDER'] = MATERIALS_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Temporary user database (replace with a real DB in production)
USERS = {
    "student1": {"password": "pass123", "role": "student"},
    "staff1": {"password": "staffpass", "role": "staff"},
}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def process_api_response(api_response):
    # This function would parse the API response and convert it to our question format
    # The exact implementation depends on the API response structure
    
    # For now, we'll use a placeholder implementation
    try:
        # Assuming the API returns a list of questions in its 'data' field
        questions_data = api_response.get('data', [])
        
        formatted_questions = []
        for q_data in questions_data:
            question_type = q_data.get('type', 'multiple-choice')
            
            if question_type == 'multiple-choice':
                formatted_questions.append({
                    "question": q_data.get('question', ''),
                    "type": "multiple-choice",
                    "options": q_data.get('options', []),
                    "correctAnswer": q_data.get('correctAnswerIndex', 0)
                })
            elif question_type == 'true-false':
                formatted_questions.append({
                    "question": q_data.get('question', ''),
                    "type": "true-false",
                    "correctAnswer": 1 if q_data.get('correctAnswer', True) else 0
                })
            elif question_type == 'fill-in-blank':
                formatted_questions.append({
                    "question": q_data.get('question', ''),
                    "type": "fill-in-blank",
                    "answer": q_data.get('answer', '')
                })
        
        # If no questions were successfully parsed, return fallback questions
        if not formatted_questions:
            return [
                {
                    "question": "What is the main topic discussed in the document?",
                    "type": "multiple-choice",
                    "options": ["Option A", "Option B", "Option C", "Option D"],
                    "correctAnswer": 0
                },
                {
                    "question": "True or False: The document mentions important concepts.",
                    "type": "true-false",
                    "correctAnswer": 0
                }
            ]
            
        return formatted_questions
        
    except Exception as e:
        print(f"Error processing API response: {str(e)}")
        # Return fallback questions if parsing fails
        return [
            {
                "question": "What is the main topic discussed in the document?",
                "type": "multiple-choice",
                "options": ["Option A", "Option B", "Option C", "Option D"],
                "correctAnswer": 0
            },
            {
                "question": "True or False: The document mentions important concepts.",
                "type": "true-false",
                "correctAnswer": 0
            }
        ]

def process_mcq_response(api_response):
    # Similar to process_api_response but specifically for MCQs
    try:
        # Assuming the API returns MCQs in a specific format
        mcq_data = api_response.get('data', [])
        
        formatted_mcqs = []
        for mcq in mcq_data:
            formatted_mcqs.append({
                "question": mcq.get('question', ''),
                "options": mcq.get('options', []),
                "correct": mcq.get('correctAnswer', '')
            })
        
        # If no MCQs were successfully parsed, return fallback MCQs
        if not formatted_mcqs:
            return [
                {
                    "question": "What is the capital of France?",
                    "options": ["Berlin", "Madrid", "Paris", "Rome"],
                    "correct": "Paris"
                },
                {
                    "question": "Which planet is known as the Red Planet?",
                    "options": ["Earth", "Mars", "Jupiter", "Venus"],
                    "correct": "Mars"
                }
            ]
            
        return formatted_mcqs
        
    except Exception as e:
        print(f"Error processing MCQ API response: {str(e)}")
        # Return fallback MCQs if parsing fails
        return [
            {
                "question": "What is the capital of France?",
                "options": ["Berlin", "Madrid", "Paris", "Rome"],
                "correct": "Paris"
            },
            {
                "question": "Which planet is known as the Red Planet?",
                "options": ["Earth", "Mars", "Jupiter", "Venus"],
                "correct": "Mars"
            }
        ]

@app.route('/')
def login_page():
    if "username" in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")
    role = data.get("role")

    user = USERS.get(username)
    if user and user["password"] == password and user["role"] == role:
        session["username"] = username
        session["role"] = role
        return jsonify({"success": True})

    return jsonify({"success": False, "message": "Invalid credentials"})

@app.route('/dashboard')
def dashboard():
    if "username" not in session:
        return redirect(url_for('login_page'))
    role = session.get("role")
    username = session.get("username")

    if role == "student":
        return render_template("student_dashboard.html", username=username, role=role)
    elif role == "staff":
        return render_template("staff_dashboard.html", username=username, role=role)
    return redirect(url_for('logout'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))

# New routes for test creation workflow
@app.route('/staff/new-test')
def new_test():
    if "username" not in session or session["role"] != "staff":
        return redirect(url_for('login_page'))
    return render_template('new_test.html', username=session["username"], role=session["role"])

@app.route('/staff/generated-questions')
def generated_questions():
    if "username" not in session or session["role"] != "staff":
        return redirect(url_for('login_page'))
    return render_template('generated_questions.html', username=session["username"], role=session["role"])

# New route for uploading materials
@app.route('/staff/upload-materials')
def upload_materials():
    if "username" not in session or session["role"] != "staff":
        return redirect(url_for('login_page'))
    return render_template('upload_materials.html', username=session["username"], role=session["role"])

@app.route('/api/generate-questions', methods=['POST'])
def generate_questions():
    if "username" not in session or session["role"] != "staff":
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    data = request.json
    pdf_name = data.get("pdfName", "")
    pdf_content = data.get("pdfContent", "")
    
    # Use the GSK API to generate questions from PDF content
    try:
        headers = {
            "Authorization": f"Bearer {GSK_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "gsk-question-generator",
            "prompt": f"Generate educational assessment questions based on this content: {pdf_content}",
            "max_tokens": 1000,
            "temperature": 0.7,
            "format": "json"
        }
        
        response = requests.post(GSK_API_ENDPOINT, headers=headers, json=payload)
        
        if response.status_code == 200:
            api_response = response.json()
            
            # Process the API response to extract questions
            generated_questions = process_api_response(api_response)
            
            return jsonify({
                "success": True, 
                "questions": generated_questions,
                "message": f"Successfully generated questions from {pdf_name}"
            })
        else:
            return jsonify({
                "success": False,
                "message": f"API Error: {response.status_code} - {response.text}"
            }), 500
            
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error generating questions: {str(e)}"
        }), 500

@app.route('/api/upload-test', methods=['POST'])
def upload_test():
    if "username" not in session or session["role"] != "staff":
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    data = request.json
    test_id = str(uuid.uuid4())
    
    test_data = {
        "id": test_id,
        "name": data.get("name", "Untitled Test"),
        "timeLimit": data.get("duration", 30),
        "questions": data.get("questions", []),
        "createdAt": datetime.now().isoformat(),
        "createdBy": session["username"]
    }
    
    with open(os.path.join(TESTS_FOLDER, f"{test_id}.json"), 'w') as f:
        json.dump(test_data, f, indent=2)
    
    return jsonify({"success": True, "id": test_id})

# New route for uploading material files
@app.route('/api/upload-material', methods=['POST'])
def upload_material():
    if "username" not in session or session["role"] != "staff":
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    # Check if the post request has the file part
    if 'materialFile' not in request.files:
        return jsonify({"success": False, "message": "No file part"}), 400
    
    file = request.files['materialFile']
    title = request.form.get('materialTitle', '')
    material_type = request.form.get('materialType', '')
    
    # If user does not select file, browser also
    # submit an empty part without filename
    if file.filename == '':
        return jsonify({"success": False, "message": "No selected file"}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Save material metadata
        material_id = str(uuid.uuid4())
        material_data = {
            "id": material_id,
            "title": title,
            "type": material_type,
            "filename": filename,
            "uploadedBy": session["username"],
            "uploadDate": datetime.now().isoformat()
        }
        
        # Load existing materials metadata
        materials_file = os.path.join(MATERIALS_FOLDER, "materials.json")
        if os.path.exists(materials_file):
            with open(materials_file, 'r') as f:
                materials = json.load(f)
        else:
            materials = []
        
        # Add new material and save
        materials.append(material_data)
        with open(materials_file, 'w') as f:
            json.dump(materials, f, indent=2)
        
        return jsonify({"success": True, "message": "Material uploaded successfully"})
    
    return jsonify({"success": False, "message": "File type not allowed"}), 400

# Route to get all materials
@app.route('/api/materials')
def get_materials():
    if "username" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    materials_file = os.path.join(MATERIALS_FOLDER, "materials.json")
    if os.path.exists(materials_file):
        with open(materials_file, 'r') as f:
            materials = json.load(f)
    else:
        materials = []
    
    return jsonify({"success": True, "materials": materials})

# Route to view a material
@app.route('/material/<material_id>')
def view_material(material_id):
    if "username" not in session:
        return redirect(url_for('login_page'))
    
    # Get material metadata
    materials_file = os.path.join(MATERIALS_FOLDER, "materials.json")
    if os.path.exists(materials_file):
        with open(materials_file, 'r') as f:
            materials = json.load(f)
        
        # Find the material with the given ID
        material = next((m for m in materials if m["id"] == material_id), None)
        if material:
            return send_from_directory(MATERIALS_FOLDER, material["filename"])
    
    return "Material not found", 404

# Route to download a material
@app.route('/material/download/<material_id>')
def download_material(material_id):
    if "username" not in session:
        return redirect(url_for('login_page'))
    
    # Get material metadata
    materials_file = os.path.join(MATERIALS_FOLDER, "materials.json")
    if os.path.exists(materials_file):
        with open(materials_file, 'r') as f:
            materials = json.load(f)
        
        # Find the material with the given ID
        material = next((m for m in materials if m["id"] == material_id), None)
        if material:
            return send_from_directory(MATERIALS_FOLDER, material["filename"], as_attachment=True)
    
    return "Material not found", 404

@app.route('/available_tests')
def available_tests():
    if "username" not in session or session["role"] != "student":
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    tests = []
    for filename in os.listdir(TESTS_FOLDER):
        if filename.endswith('.json'):
            with open(os.path.join(TESTS_FOLDER, filename), 'r') as f:
                test_data = json.load(f)
                tests.append({
                    "id": test_data["id"],
                    "name": test_data["name"],
                    "questionCount": len(test_data["questions"]),
                    "timeLimit": test_data.get("timeLimit", 30),
                })

    return jsonify({"success": True, "tests": tests})

@app.route('/get_test/<test_id>')
def get_test(test_id):
    if "username" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    test_file = os.path.join(TESTS_FOLDER, f"{test_id}.json")
    if not os.path.exists(test_file):
        return jsonify({"success": False, "message": "Test not found"}), 404

    with open(test_file, 'r') as f:
        test_data = json.load(f)

    return jsonify({"success": True, "test": test_data})

@app.route('/take_test')
def take_test():
    if "username" not in session or session["role"] != "student":
        return redirect(url_for('login_page'))
    return render_template('take_test.html')

@app.route('/submit_test', methods=['POST'])
def submit_test():
    if "username" not in session or session["role"] != "student":
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    data = request.json
    test_id = data.get('testId')
    answers = data.get('answers', [])

    test_file = os.path.join(TESTS_FOLDER, f"{test_id}.json")
    if not os.path.exists(test_file):
        return jsonify({"success": False, "message": "Test not found"}), 404

    with open(test_file, 'r') as f:
        test_data = json.load(f)

    correct_count = sum(1 for ans in answers if ans['selected'] == ans['correct'])
    score_percent = round((correct_count / len(answers)) * 100)

    result_id = str(uuid.uuid4())
    result_data = {
        "id": result_id,
        "testId": test_id,
        "testName": test_data["name"],
        "student": session["username"],
        "date": datetime.now().isoformat(),
        "scorePercent": score_percent,
        "correctCount": correct_count,
        "totalQuestions": len(answers),
        "answers": answers
    }

    with open(os.path.join(RESULTS_FOLDER, f"{result_id}.json"), 'w') as f:
        json.dump(result_data, f, indent=2)

    return jsonify({
        "success": True,
        "results": {
            "id": result_id,
            "scorePercent": score_percent,
            "correctCount": correct_count,
            "totalQuestions": len(answers),
        }
    })

@app.route('/test_history')
def test_history():
    if "username" not in session or session["role"] != "student":
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    student = session["username"]
    history = []

    for filename in os.listdir(RESULTS_FOLDER):
        if filename.endswith('.json'):
            with open(os.path.join(RESULTS_FOLDER, filename), 'r') as f:
                result_data = json.load(f)
                if result_data["student"] == student:
                    history.append({
                        "id": result_data["id"],
                        "testName": result_data["testName"],
                        "date": result_data["date"],
                        "scorePercent": result_data["scorePercent"],
                        "timeTaken": result_data.get("timeTaken", 0)
                    })

    history.sort(key=lambda x: x["date"], reverse=True)
    return jsonify({"success": True, "history": history})

@app.route('/test_results')
def test_results():
    if "username" not in session:
        return redirect(url_for('login_page'))

    result_id = request.args.get('id')
    if not result_id:
        return redirect(url_for('dashboard'))

    return render_template('test_results.html')

@app.route('/get_result/<result_id>')
def get_result(result_id):
    if "username" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    result_file = os.path.join(RESULTS_FOLDER, f"{result_id}.json")
    if not os.path.exists(result_file):
        return jsonify({"success": False, "message": "Result not found"}), 404

    with open(result_file, 'r') as f:
        result_data = json.load(f)

    if session["role"] == "student" and result_data["student"] != session["username"]:
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    return jsonify({"success": True, "result": result_data})

@app.route('/upload', methods=['POST'])
def upload():
    if "username" not in session or session["role"] != "staff":
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    try:
        # Get file content from request
        file_content = request.json.get('fileContent', '')
        
        # Use the GSK API to generate MCQs
        headers = {
            "Authorization": f"Bearer {GSK_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "gsk-question-generator",
            "prompt": f"Generate multiple choice questions based on this content: {file_content}",
            "max_tokens": 1000,
            "temperature": 0.7,
            "format": "json"
        }
        
        response = requests.post(GSK_API_ENDPOINT, headers=headers, json=payload)
        
        if response.status_code == 200:
            api_response = response.json()
            
            # Process the API response to extract MCQs
            mcqs = process_mcq_response(api_response)
            
            return jsonify({"success": True, "mcqs": mcqs})
        else:
            return jsonify({
                "success": False,
                "message": f"API Error: {response.status_code} - {response.text}"
            }), 500
            
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/save_test', methods=['POST'])
def save_test():
    if "username" not in session or session["role"] != "staff":
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    data = request.json
    test_id = str(uuid.uuid4())

    test_data = {
        "id": test_id,
        "name": data.get("name", "Untitled Test"),
        "timeLimit": data.get("timeLimit", 30),
        "questions": data.get("questions", []),
        "createdAt": datetime.now().isoformat(),
        "createdBy": session["username"]
    }

    with open(os.path.join(TESTS_FOLDER, f"{test_id}.json"), 'w') as f:
        json.dump(test_data, f, indent=2)

    return jsonify({"success": True, "id": test_id})

@app.route('/staff_tests')
def staff_tests():
    if "username" not in session or session["role"] != "staff":
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    tests = []
    for filename in os.listdir(TESTS_FOLDER):
        if filename.endswith('.json'):
            with open(os.path.join(TESTS_FOLDER, filename), 'r') as f:
                test_data = json.load(f)
                tests.append({
                    "id": test_data["id"],
                    "name": test_data["name"],
                    "questionCount": len(test_data["questions"]),
                    "timeLimit": test_data.get("timeLimit", 30),
                    "createdAt": test_data.get("createdAt", "")
                })

    tests.sort(key=lambda x: x["createdAt"], reverse=True)
    return jsonify({"success": True, "tests": tests})

@app.route('/student_results')
def student_results():
    if "username" not in session or session["role"] != "staff":
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    results = []
    for filename in os.listdir(RESULTS_FOLDER):
        if filename.endswith('.json'):
            with open(os.path.join(RESULTS_FOLDER, filename), 'r') as f:
                result_data = json.load(f)
                results.append({
                    "id": result_data["id"],
                    "student": result_data["student"],
                    "testName": result_data["testName"],
                    "date": result_data["date"],
                    "scorePercent": result_data["scorePercent"]
                })

    results.sort(key=lambda x: x["date"], reverse=True)
    return jsonify({"success": True, "results": results})

if __name__ == '__main__':
    app.run(debug=True)
