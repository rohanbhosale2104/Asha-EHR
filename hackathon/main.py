from flask import Flask, render_template, request, redirect, url_for, session, make_response, send_file
import io
import csv
import json
import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# --- Configuration ---
app = Flask(__name__)
app.secret_key = 'f2a96c2ff15682ccc1007b327991d7ca5cf7e6371278760bf894d22c25dd21fb'

# --- Language Support ---
SUPPORTED_LANGUAGES = ['english', 'hindi', 'marathi', 'punjabi', 'bengali']
DEFAULT_LANGUAGE = 'english'

FALLBACK_TRANSLATIONS = {
    'app_name': 'ASHA EHR',
    'dashboard': 'Dashboard',
    'patients': 'Patients',
    'reminders': 'Reminders',
    'reports': 'Reports',
    'profile': 'Profile',
    'logout': 'Logout',
    'english': 'English',
    'hindi': 'Hindi',
    'marathi': 'Marathi',
    'punjabi': 'Punjabi',
    'bengali': 'Bengali',
    'personal_information': 'Personal Information',
    'view_your_details': 'View your details',
    'contact': 'Contact',
    'language': 'Language',
    'sync_status': 'Sync Status',
    'privacy_security': 'Privacy & Security',
    'manage_permissions': 'Manage Permissions',
    'help_support': 'Help & Support',
    'faqs_contact': 'FAQs & Contact',
    'about': 'About',
    'app_version': 'App Version',
    'user_id': 'User ID',
    'name': 'Name',
    'role': 'Role'
}

def load_translations(lang_code):
    try:
        path = f'translations/{lang_code}.json'
        if not os.path.exists(path):
            return FALLBACK_TRANSLATIONS
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return FALLBACK_TRANSLATIONS

def get_current_language():
    return session.get('language', DEFAULT_LANGUAGE)

def gettext(key, *args):
    lang_code = get_current_language()
    translations = load_translations(lang_code)
    translation = translations.get(key, FALLBACK_TRANSLATIONS.get(key, key))
    if args:
        try:
            return translation % args
        except:
            return translation
    return translation

@app.context_processor
def inject_globals():
    return dict(
        gettext=gettext,
        current_language=get_current_language(),
        supported_languages=SUPPORTED_LANGUAGES
    )

# --- Mock Users ---
ASHA_WORKERS = [
    {'id': 'asha_1', 'name': 'Sunita Devi', 'area': 'Ward 1'},
    {'id': 'asha_2', 'name': 'Meena Kumari', 'area': 'Ward 3'},
    {'id': 'asha_3', 'name': 'Lata Patil', 'area': 'Ward 5'},
]

MOCK_USERS = {
    'demo': {'password': 'demo123', 'role': 'ASHA Worker', 'name': 'Priya Sharma'},
    'phc_1': {'password': 'phc123', 'role': 'PHC Supervisor', 'name': 'Dr. Rohan Mehra'},
}

PATIENTS = [
    {'id': 101, 'name': 'Savita Devi', 'age': '35', 'gender': 'F', 'contact': '9876543210', 'status': 'ANC Due'},
    {'id': 102, 'name': 'Ramesh Kumar', 'age': '52', 'gender': 'M', 'contact': '8765432109', 'status': 'Diabetic'},
]

NEXT_PATIENT_ID = 103

# --- Auth Decorators ---
def requires_auth(f):
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

def requires_phc(f):
    def wrapper(*args, **kwargs):
        if session.get('user_role') != 'PHC Supervisor':
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

def safe_int(v, d=0):
    try:
        return int(v)
    except:
        return d

# ================= ROUTES =================

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for(
            'phc_dashboard' if session['user_role'] == 'PHC Supervisor' else 'dashboard'
        ))
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    user_id = request.form.get('user_id')
    password = request.form.get('password')
    user = MOCK_USERS.get(user_id)

    if user and user['password'] == password:
        session['user_id'] = user_id
        session['user_name'] = user['name']
        session['user_role'] = user['role']
        session.setdefault('language', DEFAULT_LANGUAGE)
        if user['role'] == 'PHC Supervisor':
            return redirect(url_for('phc_dashboard'))
        return redirect(url_for('dashboard'))

    return render_template('login.html', error="Invalid User ID or Password")

@app.route('/phc_login')
def phc_login():
    return render_template('phc_login.html')

@app.route('/logout')
@requires_auth
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/set_language/<lang_code>')
@requires_auth
def set_language(lang_code):
    if lang_code in SUPPORTED_LANGUAGES:
        session['language'] = lang_code
    return redirect(request.referrer or url_for('dashboard'))

# ---------- ASHA DASHBOARD ----------
@app.route('/dashboard')
@requires_auth
def dashboard():
    if session['user_role'] == 'PHC Supervisor':
        return redirect(url_for('phc_dashboard'))
    return render_template(
        'dashboard.html',
        name=session['user_name'],
        role=session['user_role'],
        total_patients=len(PATIENTS),
        today_visits=3,
        pending_reminders=5,
        completed_tasks=12
    )

# ---------- PHC DASHBOARD ----------
@app.route('/phc_dashboard')
@requires_auth
@requires_phc
def phc_dashboard():
    stats = {
        'total_asha': len(ASHA_WORKERS),
        'patients_in_sector': len(PATIENTS),
        'anc_due_this_week': len([p for p in PATIENTS if p['status'] == 'ANC Due']),
        'unresolved_cases': len([p for p in PATIENTS if p['status'] in ['ANC Due', 'Critical']])
    }
    return render_template('phc_dashboard.html', stats=stats, name=session['user_name'])

# ---------- PATIENTS ----------
@app.route('/patients')
@requires_auth
def patients():
    return render_template('patients.html', patients=PATIENTS)

@app.route('/register_patient', methods=['GET', 'POST'])
@requires_auth
def register_patient():
    global NEXT_PATIENT_ID
    if request.method == 'POST':
        PATIENTS.append({
            'id': NEXT_PATIENT_ID,
            'name': request.form['name'],
            'age': request.form['age'],
            'gender': request.form['gender'],
            'contact': request.form['contact'],
            'status': request.form['status']
        })
        NEXT_PATIENT_ID += 1
        return redirect(url_for('patients'))
    return render_template('register_patient.html')

# ---------- REMINDERS ----------
@app.route('/reminders')
@requires_auth
def reminders():
    if session.get('user_role') == 'PHC Supervisor':
        return redirect(url_for('phc_dashboard'))
    return render_template('reminders.html')

# ---------- REPORTS ----------
@app.route('/reports')
@requires_auth
def reports():
    return render_template('reports.html', data={
        'total_patients': len(PATIENTS),
        'male_patients': len([p for p in PATIENTS if p['gender'] == 'M']),
        'female_patients': len([p for p in PATIENTS if p['gender'] == 'F']),
        'children': len([p for p in PATIENTS if safe_int(p['age']) < 12])
    })

# ---------- PROFILE ----------
@app.route('/profile')
@requires_auth
def profile():
    return render_template(
        'profile.html',
        name=session['user_name'],
        role=session['user_role'],
        sync_status='Connected'
    )

# ---------- PHC Pages ----------
@app.route('/asha-workers')
@requires_auth
@requires_phc
def phc_asha_workers():
    return render_template('phc_asha_workers.html', workers=ASHA_WORKERS)

@app.route('/phc_patients')
@requires_auth
@requires_phc
def phc_patients():
    return render_template('patients.html', patients=PATIENTS)

@app.route('/phc_unresolved_cases')
@requires_auth
@requires_phc
def phc_unresolved_cases():
    unresolved = [p for p in PATIENTS if p['status'] in ['ANC Due', 'Critical']]
    return render_template('phc_unresolved_cases.html', cases=unresolved)

# ---------- EXPORT CSV ----------
@app.route('/export_csv')
@requires_auth
def export_csv():
    data = [
        ['Type', 'Value'],
        ['Total Patients', str(len(PATIENTS))],
        ['Male Patients', str(len([p for p in PATIENTS if p['gender'] == 'M']))],
        ['Female Patients', str(len([p for p in PATIENTS if p['gender'] == 'F']))],
        ['Children (under 12)', str(len([p for p in PATIENTS if safe_int(p['age']) < 12]))],
    ]
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerows(data)
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=ASHA_Report.csv"
    output.headers["Content-type"] = "text/csv"
    return output

# ---------- EXPORT PDF ----------
@app.route('/export_pdf')
@requires_auth
def export_pdf():
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, height - 50, "ASHA Worker Report")
    c.setFont("Helvetica", 12)
    y = height - 100

    report_data = [
        ['Total Patients', len(PATIENTS)],
        ['Male Patients', len([p for p in PATIENTS if p['gender'] == 'M'])],
        ['Female Patients', len([p for p in PATIENTS if p['gender'] == 'F'])],
        ['Children (under 12)', len([p for p in PATIENTS if safe_int(p['age']) < 12])]
    ]

    for item in report_data:
        c.drawString(50, y, f"{item[0]}: {item[1]}")
        y -= 20

    c.showPage()
    c.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="ASHA_Report.pdf", mimetype='application/pdf')

# ---------- ABOUT PAGES ----------
@app.route('/about')
@requires_auth
def about():
    app_info = {
        'name': 'ASHA EHR',
        'version': '1.0.0',
        'description': 'This app helps ASHA workers manage patients, reminders, and reports efficiently.'
    }
    return render_template('about.html', app=app_info)

@app.route('/aboutPHC')
@requires_auth
@requires_phc
def about_phc():
    app_info = {
        'name': 'ASHA EHR',
        'version': '1.0.0',
        'description_phc': 'This PHC module allows supervisors to monitor ASHA workers, patients, and unresolved cases efficiently.'
    }
    return render_template('aboutPHC.html', app=app_info)

# ---------- CONTACT ----------
@app.route('/contact')
def contact():
    info = {
        'support_email': 'support@example.com',
        'phone': '+91 9876543210',
        'address': '123 Main Street, City, State, India'
    }
    return render_template('contact.html', info=info)

# --- RUN ---
if __name__ == '__main__':
    os.makedirs('translations', exist_ok=True)
    app.run(debug=True)
