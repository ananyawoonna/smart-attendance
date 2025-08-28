import streamlit as st
import sqlite3
import qrcode
import cv2
import numpy as np
from PIL import Image
import io
import uuid
import json
from datetime import datetime, timedelta
import math
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import base64
import os
import hashlib

# Database configuration - PERSISTENT DATABASE
DB_PATH = 'smart_attendance_system.db'

def get_db_connection():
    """Get database connection with proper setup"""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_database():
    """Initialize database with all required tables"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create attendance table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT NOT NULL,
            student_roll TEXT,
            subject TEXT NOT NULL,
            period TEXT NOT NULL,
            timestamp DATETIME NOT NULL,
            device_id TEXT NOT NULL,
            student_latitude REAL,
            student_longitude REAL,
            qr_latitude REAL,
            qr_longitude REAL,
            status TEXT DEFAULT 'present',
            marked_by TEXT,
            modified_by TEXT,
            modification_reason TEXT,
            created_date DATE DEFAULT (DATE('now'))
        )
    ''')
    
    # Create QR codes table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS qr_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            qr_id TEXT UNIQUE NOT NULL,
            subject TEXT NOT NULL,
            period TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            created_at DATETIME NOT NULL,
            expires_at DATETIME NOT NULL,
            created_by TEXT,
            is_active BOOLEAN DEFAULT 1
        )
    ''')
    
    # Create faculty table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS faculty (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            faculty_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            email TEXT,
            department TEXT,
            subjects TEXT,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'faculty',
            is_active BOOLEAN DEFAULT 1,
            last_login DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create students table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            roll_number TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            class_grade TEXT,
            department TEXT,
            email TEXT,
            phone TEXT,
            parent_phone TEXT,
            is_active BOOLEAN DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create events table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            event_date DATE NOT NULL,
            event_type TEXT DEFAULT 'holiday',
            created_by TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create announcements table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS announcements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            target_audience TEXT DEFAULT 'all',
            priority TEXT DEFAULT 'medium',
            created_by TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1
        )
    ''')
    
    # Check if default data exists
    cursor.execute("SELECT COUNT(*) FROM faculty WHERE role = 'admin'")
    admin_exists = cursor.fetchone()[0] > 0
    
    if not admin_exists:
        # Create default admin (password: admin123)
        admin_password_hash = hashlib.sha256("admin123".encode()).hexdigest()
        cursor.execute('''
            INSERT INTO faculty (faculty_id, name, email, department, password_hash, role)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ('ADMIN001', 'Principal Administrator', 'admin@school.edu', 'Administration', admin_password_hash, 'admin'))
        
        # Create sample faculty members (password: pass123)
        faculty_password_hash = hashlib.sha256("pass123".encode()).hexdigest()
        sample_faculty = [
            ('FAC001', 'Dr. Smith Johnson', 'smith@school.edu', 'Mathematics', 'Mathematics,Algebra,Geometry'),
            ('FAC002', 'Prof. Emily Davis', 'emily@school.edu', 'Science', 'Physics,Chemistry,Biology'),
            ('FAC003', 'Mr. Robert Wilson', 'robert@school.edu', 'English', 'English Literature,Grammar'),
            ('FAC004', 'Ms. Sarah Brown', 'sarah@school.edu', 'History', 'World History,Social Studies'),
            ('FAC005', 'Dr. Michael Lee', 'michael@school.edu', 'Computer Science', 'Programming,Database,Web Development')
        ]
        
        for faculty in sample_faculty:
            cursor.execute('''
                INSERT INTO faculty (faculty_id, name, email, department, subjects, password_hash)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (*faculty, faculty_password_hash))
        
        # Create sample students
        sample_students = [
            ('2024001', 'John Smith', '10-A', 'Science', 'john@student.edu', '9876543210', '9876543211'),
            ('2024002', 'Jane Doe', '10-A', 'Science', 'jane@student.edu', '9876543212', '9876543213'),
            ('2024003', 'Bob Johnson', '10-B', 'Commerce', 'bob@student.edu', '9876543214', '9876543215'),
            ('2024004', 'Alice Wilson', '11-A', 'Science', 'alice@student.edu', '9876543216', '9876543217'),
            ('2024005', 'Charlie Brown', '11-B', 'Arts', 'charlie@student.edu', '9876543218', '9876543219')
        ]
        
        for student in sample_students:
            cursor.execute('''
                INSERT INTO students (roll_number, name, class_grade, department, email, phone, parent_phone)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', student)
    
    conn.commit()
    conn.close()

def hash_password(password):
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, hashed):
    """Verify password against hash"""
    return hashlib.sha256(password.encode()).hexdigest() == hashed

def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two GPS coordinates"""
    R = 6371000  # Earth's radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c

def generate_qr_code(qr_data):
    """Generate QR code image"""
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(json.dumps(qr_data))
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert PIL image to bytes for Streamlit
    img_buffer = io.BytesIO()
    img.save(img_buffer, format='PNG')
    img_buffer.seek(0)
    
    return img, img_buffer.getvalue()

def read_qr_code(image):
    """Read QR code from uploaded image"""
    try:
        # Convert PIL image to OpenCV format
        opencv_img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        # Initialize QR code detector
        detector = cv2.QRCodeDetector()
        
        # Detect and decode QR code
        data, vertices_array, binary_qrcode = detector.detectAndDecode(opencv_img)
        
        if vertices_array is not None and len(data) > 0:
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                return None
        return None
    except Exception as e:
        st.error(f"Error reading QR code: {str(e)}")
        return None

# HOME PAGE
def home_page():
    """Main home page"""
    st.title("🎓 Smart Attendance Management System")
    st.markdown("### Welcome to the Advanced Smart Attendance App!")
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("👨‍🏫 Faculty & Admin Portal")
        st.markdown("""
        **For Teachers & Administrators:**
        • 📱 Generate QR codes for attendance
        • 📊 View and analyze attendance records
        • ✏️ Edit attendance records
        • 🏛️ Admin dashboard with advanced analytics
        • 👥 Manage students and staff
        • 📢 Send announcements
        """)
        if st.button("🔐 Faculty/Admin Login", use_container_width=True, type="primary"):
            st.session_state.page = 'faculty_login'
            st.rerun()
    
    with col2:
        st.subheader("🎓 Student Portal")
        st.markdown("""
        **For Students:**
        • 📱 Scan QR codes for quick attendance
        • 🌍 Automatic GPS location verification
        • ✅ Instant attendance confirmation
        • 📊 View your attendance history
        • 📧 Get attendance notifications
        """)
        if st.button("📱 Student App", use_container_width=True, type="secondary"):
            st.session_state.page = 'student_app'
            st.rerun()
    
    # Quick stats
    st.markdown("---")
    st.subheader("📈 Today's Quick Stats")
    
    conn = get_db_connection()
    try:
        today = datetime.now().date()
        total_attendance_today = pd.read_sql_query(
            "SELECT COUNT(*) as count FROM attendance WHERE DATE(timestamp) = ?", 
            conn, params=[today]
        ).iloc[0]['count']
        
        total_students = pd.read_sql_query(
            "SELECT COUNT(*) as count FROM students WHERE is_active = 1", 
            conn
        ).iloc[0]['count']
        
        total_faculty = pd.read_sql_query(
            "SELECT COUNT(*) as count FROM faculty WHERE is_active = 1 AND role != 'admin'", 
            conn
        ).iloc[0]['count']
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Today's Attendance", total_attendance_today)
        with col2:
            st.metric("Total Students", total_students)
        with col3:
            st.metric("Faculty Members", total_faculty)
        with col4:
            attendance_rate = f"{(total_attendance_today/max(total_students,1)*100):.1f}%" if total_students > 0 else "0%"
            st.metric("Attendance Rate", attendance_rate)
            
    except Exception as e:
        st.info("📊 No attendance data available yet. Start by logging in as faculty!")
    finally:
        conn.close()

# FACULTY LOGIN PAGE
def faculty_login():
    """Faculty and Admin login page"""
    st.title("🔐 Faculty & Admin Login")
    
    if st.button("🏠 Back to Home"):
        st.session_state.page = "home"
        st.rerun()
    
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("faculty_login_form"):
            st.markdown("### Please enter your credentials")
            
            faculty_id = st.text_input("👤 Faculty ID", placeholder="e.g., FAC001 or ADMIN001")
            password = st.text_input("🔒 Password", type="password", placeholder="Enter your password")
            
            st.markdown("---")
            login_button = st.form_submit_button("🚀 Login", use_container_width=True, type="primary")
            
            if login_button:
                if not faculty_id or not password:
                    st.error("❌ Please enter both Faculty ID and Password!")
                    return
                
                conn = get_db_connection()
                cursor = conn.cursor()
                
                try:
                    cursor.execute('''
                        SELECT faculty_id, name, role, department, password_hash, is_active
                        FROM faculty 
                        WHERE faculty_id = ?
                    ''', (faculty_id.upper(),))
                    
                    faculty = cursor.fetchone()
                    
                    if faculty and faculty[5]:  # Check if active
                        if verify_password(password, faculty[4]):  # Verify password
                            # Update last login
                            cursor.execute('''
                                UPDATE faculty SET last_login = ? WHERE faculty_id = ?
                            ''', (datetime.now().isoformat(), faculty_id.upper()))
                            conn.commit()
                            
                            # Set session state
                            st.session_state.faculty_logged_in = True
                            st.session_state.faculty_id = faculty[0]
                            st.session_state.faculty_name = faculty[1]
                            st.session_state.faculty_role = faculty[2]
                            st.session_state.faculty_department = faculty[3]
                            
                            # Redirect based on role
                            if faculty[2] == 'admin':
                                st.session_state.page = "admin_dashboard"
                                st.success(f"✅ Welcome {faculty[1]}! Redirecting to Admin Dashboard...")
                            else:
                                st.session_state.page = "faculty_dashboard"
                                st.success(f"✅ Welcome {faculty[1]}! Redirecting to Faculty Dashboard...")
                            
                            st.rerun()
                        else:
                            st.error("❌ Invalid password!")
                    else:
                        st.error("❌ Invalid Faculty ID or account is inactive!")
                        
                except Exception as e:
                    st.error(f"❌ Login error: {str(e)}")
                finally:
                    conn.close()
        
        # Demo credentials info
        with st.expander("🆘 Demo Credentials"):
            st.markdown("""
            **Admin Account:**
            - Faculty ID: `ADMIN001`
            - Password: `admin123`
            
            **Sample Faculty Accounts:**
            - Faculty ID: `FAC001` (Dr. Smith) - Password: `pass123`
            - Faculty ID: `FAC002` (Prof. Emily) - Password: `pass123`
            - Faculty ID: `FAC003` (Mr. Robert) - Password: `pass123`
            """)

# FACULTY DASHBOARD
def faculty_dashboard():
    """Faculty dashboard page"""
    st.title(f"👨‍🏫 Faculty Dashboard")
    st.markdown(f"**Welcome back, {st.session_state.faculty_name}!** | Department: {st.session_state.faculty_department}")
    
    # Quick action buttons
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        if st.button("📱 Generate QR", use_container_width=True):
            st.session_state.page = "generate_qr"
            st.rerun()
    
    with col2:
        if st.button("📋 View Records", use_container_width=True):
            st.session_state.page = "view_attendance"
            st.rerun()
    
    with col3:
        if st.button("✏️ Edit Attendance", use_container_width=True):
            st.session_state.page = "edit_attendance"
            st.rerun()
    
    with col4:
        if st.button("📊 Analytics", use_container_width=True):
            st.session_state.page = "analytics"
            st.rerun()
    
    with col5:
        if st.button("🚪 Logout", use_container_width=True, type="secondary"):
            # Clear session
            for key in ['faculty_logged_in', 'faculty_id', 'faculty_name', 'faculty_role', 'faculty_department']:
                if key in st.session_state:
                    del st.session_state[key]
            st.session_state.page = "home"
            st.success("✅ Logged out successfully!")
            st.rerun()
    
    st.markdown("---")
    
    # Today's summary
    today = datetime.now().date()
    conn = get_db_connection()
    
    try:
        # Get today's stats
        qr_today = pd.read_sql_query('''
            SELECT COUNT(*) as count FROM qr_codes 
            WHERE DATE(created_at) = ? AND created_by = ?
        ''', conn, params=[today, st.session_state.faculty_id])
        
        attendance_today = pd.read_sql_query('''
            SELECT COUNT(*) as count FROM attendance 
            WHERE DATE(timestamp) = ? AND marked_by = ?
        ''', conn, params=[today, st.session_state.faculty_id])
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("QR Codes Generated Today", qr_today.iloc[0]['count'])
        with col2:
            st.metric("Students Attended Today", attendance_today.iloc[0]['count'])
        with col3:
            avg_attendance = "85%" if attendance_today.iloc[0]['count'] > 0 else "0%"
            st.metric("Average Class Attendance", avg_attendance)
        
        # Recent activity
        st.subheader("📋 Recent Activity")
        recent_attendance = pd.read_sql_query('''
            SELECT student_name, subject, period, timestamp, status
            FROM attendance 
            WHERE marked_by = ? 
            ORDER BY timestamp DESC LIMIT 10
        ''', conn, params=[st.session_state.faculty_id])
        
        if not recent_attendance.empty:
            st.dataframe(recent_attendance, use_container_width=True)
        else:
            st.info("🔄 No recent attendance records. Generate a QR code to start taking attendance!")
            
    except Exception as e:
        st.error(f"Error loading dashboard data: {str(e)}")
    finally:
        conn.close()

# ADMIN DASHBOARD
def admin_dashboard():
    """Admin dashboard with comprehensive features"""
    st.title(f"🏛️ Admin Dashboard")
    st.markdown(f"**Welcome {st.session_state.faculty_name}!** | Role: Administrator")
    
    # Logout button at top
    if st.button("🚪 Logout", key="admin_logout"):
        for key in ['faculty_logged_in', 'faculty_id', 'faculty_name', 'faculty_role', 'faculty_department']:
            if key in st.session_state:
                del st.session_state[key]
        st.session_state.page = "home"
        st.rerun()
    
    st.markdown("---")
    
    # Navigation tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Overview", "📱 QR Codes", "📋 Attendance", "👥 Users", "📢 Announcements"
    ])
    
    with tab1:
        admin_overview()
    
    with tab2:
        if st.button("📱 Generate New QR Code", use_container_width=True):
            st.session_state.page = "generate_qr"
            st.rerun()
        
        # Show recent QR codes
        st.subheader("Recent QR Codes")
        conn = get_db_connection()
        qr_df = pd.read_sql_query('''
            SELECT subject, period, created_by, created_at, expires_at, is_active
            FROM qr_codes 
            ORDER BY created_at DESC LIMIT 10
        ''', conn)
        conn.close()
        
        if not qr_df.empty:
            st.dataframe(qr_df, use_container_width=True)
    
    with tab3:
        if st.button("📋 View All Attendance", use_container_width=True):
            st.session_state.page = "view_attendance"
            st.rerun()
        
        if st.button("✏️ Edit Attendance", use_container_width=True):
            st.session_state.page = "edit_attendance"
            st.rerun()
        
        # Today's attendance summary
        st.subheader("Today's Attendance Summary")
        conn = get_db_connection()
        today_attendance = pd.read_sql_query('''
            SELECT subject, period, COUNT(*) as student_count
            FROM attendance 
            WHERE DATE(timestamp) = DATE('now')
            GROUP BY subject, period
            ORDER BY student_count DESC
        ''', conn)
        conn.close()
        
        if not today_attendance.empty:
            st.dataframe(today_attendance, use_container_width=True)
        else:
            st.info("No attendance recorded today yet.")
    
    with tab4:
        user_management()
    
    with tab5:
        announcements_management()

def admin_overview():
    """Admin overview with stats and charts"""
    st.subheader("📈 School Statistics Overview")
    
    conn = get_db_connection()
    
    # Get key metrics
    try:
        today = datetime.now().date()
        
        # Today's metrics
        today_attendance = pd.read_sql_query(
            "SELECT COUNT(*) as count FROM attendance WHERE DATE(timestamp) = ?", 
            conn, params=[today]
        ).iloc[0]['count']
        
        total_students = pd.read_sql_query(
            "SELECT COUNT(*) as count FROM students WHERE is_active = 1", conn
        ).iloc[0]['count']
        
        total_faculty = pd.read_sql_query(
            "SELECT COUNT(*) as count FROM faculty WHERE is_active = 1 AND role != 'admin'", conn
        ).iloc[0]['count']
        
        total_qr_codes = pd.read_sql_query(
            "SELECT COUNT(*) as count FROM qr_codes WHERE DATE(created_at) = ?", 
            conn, params=[today]
        ).iloc[0]['count']
        
        # Display metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Today's Attendance", today_attendance)
        with col2:
            st.metric("Total Students", total_students)
        with col3:
            st.metric("Active Faculty", total_faculty)
        with col4:
            st.metric("QR Codes Today", total_qr_codes)
        
        # Charts
        col1, col2 = st.columns(2)
        
        with col1:
            # Weekly attendance trend
            weekly_data = pd.read_sql_query('''
                SELECT DATE(timestamp) as date, COUNT(*) as attendance
                FROM attendance 
                WHERE timestamp >= date('now', '-7 days')
                GROUP BY DATE(timestamp)
                ORDER BY date
            ''', conn)
            
            if not weekly_data.empty:
                fig = px.line(weekly_data, x='date', y='attendance', 
                             title="📈 Weekly Attendance Trend")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No weekly data available yet.")
        
        with col2:
            # Subject-wise distribution
            subject_data = pd.read_sql_query('''
                SELECT subject, COUNT(*) as count
                FROM attendance 
                WHERE timestamp >= date('now', '-7 days')
                GROUP BY subject
                ORDER BY count DESC
            ''', conn)
            
            if not subject_data.empty:
                fig = px.pie(subject_data, values='count', names='subject',
                           title="📚 Subject-wise Attendance (This Week)")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No subject data available yet.")
                
    except Exception as e:
        st.error(f"Error loading overview data: {str(e)}")
    finally:
        conn.close()

def user_management():
    """User management interface"""
    st.subheader("👥 User Management")
    
    # Add new faculty
    with st.expander("➕ Add New Faculty"):
        with st.form("add_faculty_form"):
            col1, col2 = st.columns(2)
            with col1:
                new_faculty_id = st.text_input("Faculty ID", placeholder="FAC006")
                new_name = st.text_input("Full Name")
                new_email = st.text_input("Email")
            
            with col2:
                new_department = st.text_input("Department")
                new_subjects = st.text_input("Subjects (comma separated)")
                new_password = st.text_input("Password", type="password")
            
            if st.form_submit_button("Add Faculty"):
                if new_faculty_id and new_name and new_password:
                    conn = get_db_connection()
                    try:
                        password_hash = hash_password(new_password)
                        cursor = conn.cursor()
                        cursor.execute('''
                            INSERT INTO faculty (faculty_id, name, email, department, subjects, password_hash)
                            VALUES (?, ?, ?, ?, ?, ?)
                        ''', (new_faculty_id.upper(), new_name, new_email, new_department, new_subjects, password_hash))
                        conn.commit()
                        st.success(f"✅ Faculty {new_faculty_id} added successfully!")
                    except sqlite3.IntegrityError:
                        st.error("❌ Faculty ID already exists!")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
                    finally:
                        conn.close()
                else:
                    st.error("❌ Please fill in required fields!")
    
    # Show existing faculty
    st.subheader("📋 Current Faculty")
    conn = get_db_connection()
    faculty_df = pd.read_sql_query('''
        SELECT faculty_id, name, department, subjects, is_active, last_login
        FROM faculty 
        WHERE role != 'admin'
        ORDER BY name
    ''', conn)
    conn.close()
    
    if not faculty_df.empty:
        st.dataframe(faculty_df, use_container_width=True)

def announcements_management():
    """Announcements management"""
    st.subheader("📢 Announcements Management")
    
    # Create new announcement
    with st.form("new_announcement_form"):
        col1, col2 = st.columns([2, 1])
        with col1:
            title = st.text_input("Announcement Title")
            message = st.text_area("Message", height=100)
        
        with col2:
            target = st.selectbox("Target Audience", ["all", "faculty", "students"])
            priority = st.selectbox("Priority", ["high", "medium", "low"])
        
        if st.form_submit_button("📤 Create Announcement"):
            if title and message:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO announcements (title, message, target_audience, priority, created_by)
                    VALUES (?, ?, ?, ?, ?)
                ''', (title, message, target, priority, st.session_state.faculty_id))
                conn.commit()
                conn.close()
                st.success("✅ Announcement created successfully!")
            else:
                st.error("❌ Please fill in all fields!")
    
    # Show recent announcements
    st.subheader("📋 Recent Announcements")
    conn = get_db_connection()
    announcements_df = pd.read_sql_query('''
        SELECT title, target_audience, priority, created_at, is_active
        FROM announcements 
        ORDER BY created_at DESC LIMIT 10
    ''', conn)
    conn.close()
    
    if not announcements_df.empty:
        st.dataframe(announcements_df, use_container_width=True)

# GENERATE QR CODE PAGE
def generate_qr_page():
    """Generate QR code page"""
    st.title("📱 Generate QR Code for Attendance")
    
    # Back button
    back_page = "admin_dashboard" if st.session_state.get('faculty_role') == 'admin' else "faculty_dashboard"
    if st.button("🏠 Back to Dashboard"):
        st.session_state.page = back_page
        st.rerun()
    
    st.markdown("---")
    
    with st.form("qr_generation_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            subject = st.text_input("Subject Name", placeholder="e.g., Mathematics")
            period = st.selectbox("Period", ["Period 1", "Period 2", "Period 3", "Period 4", "Period 5", "Period 6"])
        
        with col2:
            latitude = st.number_input("Classroom Latitude", value=17.6868, format="%.6f")
            longitude = st.number_input("Classroom Longitude", value=83.2185, format="%.6f")
        
        duration = st.slider("QR Code Valid Duration (minutes)", 5, 120, 30)
        generate_button = st.form_submit_button("🎯 Generate QR Code", type="primary")
        
        if generate_button and subject:
            qr_id = str(uuid.uuid4())
            created_at = datetime.now()
            expires_at = created_at + timedelta(minutes=duration)
            
            qr_data = {
                "qr_id": qr_id,
                "subject": subject,
                "period": period,
                "latitude": latitude,
                "longitude": longitude,
                "created_at": created_at.isoformat(),
                "expires_at": expires_at.isoformat()
            }
            
            # Save to database
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO qr_codes (qr_id, subject, period, latitude, longitude, created_at, expires_at, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (qr_id, subject, period, latitude, longitude, created_at.isoformat(), expires_at.isoformat(), st.session_state.faculty_id))
            conn.commit()
            conn.close()
            
            # Generate QR code image
            qr_img, qr_img_bytes = generate_qr_code(qr_data)
            
            st.success("✅ QR Code Generated Successfully!")
            
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.image(qr_img_bytes, caption=f"QR Code for {subject} - {period}", width=300)
            
            st.info(f"📍 Location: {latitude}, {longitude}")
            st.info(f"⏰ Valid until: {expires_at.strftime('%Y-%m-%d %H:%M:%S')}")
            st.info(f"👨‍🏫 Created by: {st.session_state.faculty_name}")
            
            # Download button
            st.download_button(
                label="📥 Download QR Code",
                data=qr_img_bytes,
                file_name=f"qr_code_{subject}_{period}_{datetime.now().strftime('%Y%m%d_%H%M')}.png",
                mime="image/png"
            )

# VIEW ATTENDANCE PAGE
def view_attendance():
    """View attendance records"""
    st.title("📋 Attendance Records")
    
    # Back button
    back_page = "admin_dashboard" if st.session_state.get('faculty_role') == 'admin' else "faculty_dashboard"
    if st.button("🏠 Back to Dashboard"):
        st.session_state.page = back_page
        st.rerun()
    
    conn = get_db_connection()
    
    # Get all attendance records
    df = pd.read_sql_query('''
        SELECT id, student_name, student_roll, subject, period, 
               timestamp, status, marked_by, student_latitude, student_longitude
        FROM attendance 
        ORDER BY timestamp DESC
    ''', conn)
    conn.close()
    
    if not df.empty:
        st.subheader("🔍 Filter Records")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            subjects = ["All"] + sorted(df['subject'].unique().tolist())
            selected_subject = st.selectbox("Filter by Subject", subjects)
        
        with col2:
            periods = ["All"] + sorted(df['period'].unique().tolist())
            selected_period = st.selectbox("Filter by Period", periods)
        
        with col3:
            date_filter = st.date_input("Filter by Date", value=datetime.now().date())
        
        with col4:
            status_filter = st.selectbox("Filter by Status", ["All", "present", "absent", "late"])
        
        # Apply filters
        filtered_df = df.copy()
        
        if selected_subject != "All":
            filtered_df = filtered_df[filtered_df['subject'] == selected_subject]
        
        if selected_period != "All":
            filtered_df = filtered_df[filtered_df['period'] == selected_period]
        
        if date_filter:
            filtered_df['date'] = pd.to_datetime(filtered_df['timestamp'], format='mixed').dt.date
            filtered_df = filtered_df[filtered_df['date'] == date_filter]
        
        if status_filter != "All":
            filtered_df = filtered_df[filtered_df['status'] == status_filter]
        
        # Display results
        st.subheader(f"📊 Found {len(filtered_df)} Records")
        
        if not filtered_df.empty:
            # Display dataframe
            display_df = filtered_df[['student_name', 'student_roll', 'subject', 'period', 'timestamp', 'status', 'marked_by']]
            st.dataframe(display_df, use_container_width=True)
            
            # Export button
            if st.button("📥 Export to CSV"):
                csv = display_df.to_csv(index=False)
                st.download_button(
                    label="💾 Download CSV File",
                    data=csv,
                    file_name=f"attendance_records_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv"
                )
        else:
            st.info("No records found with the selected filters.")
    else:
        st.info("📊 No attendance records found. Generate QR codes and have students scan them!")

# EDIT ATTENDANCE PAGE
def edit_attendance():
    """Edit attendance records"""
    st.title("✏️ Edit Attendance Records")
    
    # Back button
    back_page = "admin_dashboard" if st.session_state.get('faculty_role') == 'admin' else "faculty_dashboard"
    if st.button("🏠 Back to Dashboard"):
        st.session_state.page = back_page
        st.rerun()
    
    conn = get_db_connection()
    
    # Search interface
    st.subheader("🔍 Search Records to Edit")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        search_name = st.text_input("Student Name", placeholder="Enter student name")
    with col2:
        search_subject = st.text_input("Subject", placeholder="Enter subject")
    with col3:
        search_date = st.date_input("Date", value=datetime.now().date())
    
    # Get records based on search
    query = '''
        SELECT id, student_name, student_roll, subject, period, 
               DATE(timestamp) as date, status, marked_by, timestamp
        FROM attendance 
        WHERE 1=1
    '''
    params = []
    
    if search_name:
        query += " AND student_name LIKE ?"
        params.append(f"%{search_name}%")
    
    if search_subject:
        query += " AND subject LIKE ?"
        params.append(f"%{search_subject}%")
    
    if search_date:
        query += " AND DATE(timestamp) = ?"
        params.append(search_date.strftime('%Y-%m-%d'))
    
    query += " ORDER BY timestamp DESC LIMIT 50"
    
    df = pd.read_sql_query(query, conn, params=params)
    
    if not df.empty:
        st.subheader("📋 Select Record to Edit")
        
        # Display records for selection
        for idx, row in df.iterrows():
            col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
            
            with col1:
                st.write(f"**{row['student_name']}** ({row['student_roll']})")
            with col2:
                st.write(f"{row['subject']} - {row['period']}")
            with col3:
                st.write(f"{row['date']} - Status: **{row['status']}**")
            with col4:
                if st.button("✏️ Edit", key=f"edit_{row['id']}"):
                    st.session_state.edit_record_id = row['id']
        
        # Edit form
        if 'edit_record_id' in st.session_state:
            record_id = st.session_state.edit_record_id
            selected_record = df[df['id'] == record_id].iloc[0]
            
            st.markdown("---")
            st.subheader(f"✏️ Editing Record for {selected_record['student_name']}")
            
            with st.form("edit_attendance_form"):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    new_status = st.selectbox(
                        "Status", 
                        ["present", "absent", "late"],
                        index=["present", "absent", "late"].index(selected_record['status'])
                    )
                
                with col2:
                    modification_reason = st.text_input("Reason for Change", placeholder="e.g., Technical issue, Late arrival")
                
                with col3:
                    st.write("**Original Details:**")
                    st.write(f"Student: {selected_record['student_name']}")
                    st.write(f"Subject: {selected_record['subject']}")
                    st.write(f"Period: {selected_record['period']}")
                    st.write(f"Date: {selected_record['date']}")
                    st.write(f"Current Status: {selected_record['status']}")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("💾 Save Changes", type="primary"):
                        # Update the record
                        cursor = conn.cursor()
                        cursor.execute('''
                            UPDATE attendance 
                            SET status = ?, modified_by = ?, modification_reason = ?
                            WHERE id = ?
                        ''', (new_status, st.session_state.faculty_id, modification_reason, record_id))
                        conn.commit()
                        
                        st.success(f"✅ Record updated! Status changed from '{selected_record['status']}' to '{new_status}'")
                        
                        # Clear the edit state
                        if 'edit_record_id' in st.session_state:
                            del st.session_state.edit_record_id
                        st.rerun()
                
                with col2:
                    if st.form_submit_button("❌ Cancel"):
                        if 'edit_record_id' in st.session_state:
                            del st.session_state.edit_record_id
                        st.rerun()
    
    else:
        st.info("🔍 No records found. Try adjusting your search criteria.")
    
    conn.close()

# ANALYTICS PAGE
def analytics():
    """Analytics dashboard"""
    st.title("📊 Attendance Analytics")
    
    # Back button
    back_page = "admin_dashboard" if st.session_state.get('faculty_role') == 'admin' else "faculty_dashboard"
    if st.button("🏠 Back to Dashboard"):
        st.session_state.page = back_page
        st.rerun()
    
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT * FROM attendance", conn)
    conn.close()
    
    if not df.empty:
        # Convert timestamp to proper format
        df['date'] = pd.to_datetime(df['timestamp'], format='mixed').dt.date
        df['datetime'] = pd.to_datetime(df['timestamp'], format='mixed')
        
        # Time range selector
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("From Date", value=datetime.now().date() - timedelta(days=30))
        with col2:
            end_date = st.date_input("To Date", value=datetime.now().date())
        
        # Filter by date range
        filtered_df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
        
        if not filtered_df.empty:
            st.markdown("---")
            
            # Key metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Records", len(filtered_df))
            with col2:
                present_count = len(filtered_df[filtered_df['status'] == 'present'])
                st.metric("Present", present_count)
            with col3:
                absent_count = len(filtered_df[filtered_df['status'] == 'absent'])
                st.metric("Absent", absent_count)
            with col4:
                attendance_rate = f"{(present_count/len(filtered_df)*100):.1f}%" if len(filtered_df) > 0 else "0%"
                st.metric("Attendance Rate", attendance_rate)
            
            # Charts
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("📊 Subject-wise Distribution")
                subject_counts = filtered_df['subject'].value_counts()
                if not subject_counts.empty:
                    fig_pie = px.pie(values=subject_counts.values, names=subject_counts.index)
                    st.plotly_chart(fig_pie, use_container_width=True)
            
            with col2:
                st.subheader("📊 Status Distribution")
                status_counts = filtered_df['status'].value_counts()
                if not status_counts.empty:
                    fig_bar = px.bar(x=status_counts.index, y=status_counts.values)
                    fig_bar.update_layout(xaxis_title="Status", yaxis_title="Count")
                    st.plotly_chart(fig_bar, use_container_width=True)
            
            # Daily trend
            st.subheader("📈 Daily Attendance Trend")
            daily_counts = filtered_df['date'].value_counts().sort_index()
            if not daily_counts.empty:
                fig_line = px.line(x=daily_counts.index, y=daily_counts.values)
                fig_line.update_layout(xaxis_title="Date", yaxis_title="Number of Students")
                st.plotly_chart(fig_line, use_container_width=True)
            
            # Period-wise analysis
            st.subheader("🕐 Period-wise Attendance")
            period_counts = filtered_df['period'].value_counts()
            if not period_counts.empty:
                fig_period = px.bar(x=period_counts.index, y=period_counts.values)
                fig_period.update_layout(xaxis_title="Period", yaxis_title="Number of Students")
                st.plotly_chart(fig_period, use_container_width=True)
        
        else:
            st.info("No data available for the selected date range.")
    else:
        st.info("📊 No attendance data available yet.")

# STUDENT APP
def student_app():
    """Student attendance app"""
    st.title("🎓 Student Attendance App")
    
    if st.button("🏠 Back to Home"):
        st.session_state.page = "home"
        st.rerun()
    
    st.markdown("---")
    st.subheader("📱 Scan QR Code for Attendance")
    st.info("💡 Upload the QR code image generated by your teacher to mark attendance.")
    
    uploaded_file = st.file_uploader("📤 Upload QR Code Image", type=['png', 'jpg', 'jpeg'])
    
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.image(image, caption="Uploaded QR Code", width=300)
        
        st.markdown("---")
        
        qr_data = read_qr_code(image)
        
        if qr_data and 'qr_id' in qr_data:
            st.success("✅ QR Code detected successfully!")
            
            # Display QR code information
            col1, col2 = st.columns(2)
            with col1:
                st.info(f"📚 **Subject:** {qr_data['subject']}")
                st.info(f"🕐 **Period:** {qr_data['period']}")
            
            with col2:
                st.info(f"📍 **Location:** {qr_data['latitude']}, {qr_data['longitude']}")
                try:
                    expires_at = datetime.fromisoformat(qr_data['expires_at'])
                    if datetime.now() > expires_at:
                        st.warning(f"⚠️ **QR Code expired** at {expires_at.strftime('%Y-%m-%d %H:%M:%S')}")
                    else:
                        st.info(f"⏰ **Valid until:** {expires_at.strftime('%Y-%m-%d %H:%M:%S')}")
                except:
                    st.info("⏰ **Validity:** Checking...")
            
            # Verify QR code exists in database
            conn = get_db_connection()
            cursor = conn.cursor()
            
            try:
                cursor.execute('''
                    SELECT * FROM qr_codes WHERE qr_id = ? AND is_active = 1
                ''', (qr_data['qr_id'],))
                
                qr_record = cursor.fetchone()
                
                if qr_record:
                    st.markdown("---")
                    st.subheader("👤 Enter Your Details")
                    
                    with st.form("attendance_form"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            student_name = st.text_input("📝 Full Name", placeholder="Enter your full name")
                            student_roll = st.text_input("🎫 Roll Number", placeholder="Enter your roll number")
                        
                        with col2:
                            student_lat = st.number_input("📍 Your Latitude", value=17.6868, format="%.6f", 
                                                        help="Your current GPS latitude")
                            student_lon = st.number_input("📍 Your Longitude", value=83.2185, format="%.6f",
                                                        help="Your current GPS longitude")
                        
                        submit_attendance = st.form_submit_button("✅ Mark My Attendance", type="primary")
                        
                        if submit_attendance and student_name.strip() and student_roll.strip():
                            # Check for duplicate attendance
                            today = datetime.now().date().isoformat()
                            cursor.execute('''
                                SELECT COUNT(*) FROM attendance 
                                WHERE student_name = ? AND subject = ? AND period = ? 
                                AND DATE(timestamp) = ?
                            ''', (student_name.strip(), qr_data['subject'], qr_data['period'], today))
                            
                            existing_count = cursor.fetchone()[0]
                            
                            if existing_count > 0:
                                st.warning("⚠️ You have already marked attendance for this subject today!")
                            else:
                                # Check location distance
                                distance = calculate_distance(
                                    float(qr_data['latitude']), float(qr_data['longitude']),
                                    student_lat, student_lon
                                )
                                
                                st.info(f"📏 **Distance from classroom:** {distance:.2f} meters")
                                
                                # Allow attendance if within reasonable distance (1km for testing)
                                if distance <= 1000:  # 1000 meters = 1km
                                    device_id = str(uuid.uuid4())
                                    
                                    # Save attendance record
                                    cursor.execute('''
                                        INSERT INTO attendance (
                                            student_name, student_roll, subject, period, timestamp, device_id,
                                            student_latitude, student_longitude, qr_latitude, qr_longitude, 
                                            status, marked_by
                                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                    ''', (
                                        student_name.strip(), student_roll.strip(), qr_data['subject'], qr_data['period'],
                                        datetime.now().isoformat(), device_id,
                                        student_lat, student_lon, qr_data['latitude'], qr_data['longitude'], 
                                        'present', 'student_app'
                                    ))
                                    conn.commit()
                                    
                                    st.success("🎉 **Attendance marked successfully!**")
                                    st.balloons()
                                    
                                    # Show confirmation details
                                    st.success(f"""
                                    ✅ **Confirmation Details:**
                                    - **Student:** {student_name} ({student_roll})
                                    - **Subject:** {qr_data['subject']}
                                    - **Period:** {qr_data['period']}
                                    - **Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                                    - **Status:** Present
                                    """)
                                    
                                else:
                                    st.error(f"""
                                    ❌ **Location verification failed!**
                                    
                                    You are **{distance:.2f} meters** away from the classroom.
                                    Maximum allowed distance is **1000 meters**.
                                    
                                    Please move closer to the classroom and try again.
                                    """)
                        
                        elif submit_attendance:
                            st.error("❌ Please enter both your name and roll number!")
                
                else:
                    st.error("❌ **Invalid QR Code!** This QR code is not found in the system or has been deactivated.")
                    
            except Exception as e:
                st.error(f"❌ **Database error:** {str(e)}")
            finally:
                conn.close()
        
        else:
            st.error("""
            ❌ **Unable to read QR code!** 
            
            Please ensure:
            - The image is clear and well-lit
            - The QR code is fully visible
            - The image format is PNG, JPG, or JPEG
            - The QR code was generated by your school's system
            """)
            
            if qr_data:
                with st.expander("🔍 Debug Information"):
                    st.json(qr_data)

# MAIN APPLICATION
def main():
    """Main application function"""
    st.set_page_config(
        page_title="Smart Attendance System",
        page_icon="🎓",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    # Initialize database
    init_database()
    
    # Initialize session state
    if 'page' not in st.session_state:
        st.session_state.page = 'home'
    if 'faculty_logged_in' not in st.session_state:
        st.session_state.faculty_logged_in = False
    
    # Custom CSS for better styling
    st.markdown("""
    <style>
    .main > div {
        padding-top: 2rem;
    }
    .stButton > button {
        border-radius: 10px;
        border: none;
        font-weight: bold;
        transition: all 0.3s;
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(45deg, #667eea 0%, #764ba2 100%);
        color: white;
    }
    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(45deg, #764ba2 0%, #667eea 100%);
        transform: translateY(-2px);
    }
    .stButton > button[kind="secondary"] {
        background: linear-gradient(45deg, #ffeaa7 0%, #fab1a0 100%);
        color: #2d3436;
    }
    .stMetric {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Page routing
    try:
        if st.session_state.page == 'home':
            home_page()
        elif st.session_state.page == 'faculty_login':
            faculty_login()
        elif st.session_state.page == 'faculty_dashboard' and st.session_state.get('faculty_logged_in'):
            faculty_dashboard()
        elif st.session_state.page == 'admin_dashboard' and st.session_state.get('faculty_logged_in') and st.session_state.get('faculty_role') == 'admin':
            admin_dashboard()
        elif st.session_state.page == 'generate_qr' and st.session_state.get('faculty_logged_in'):
            generate_qr_page()
        elif st.session_state.page == 'view_attendance' and st.session_state.get('faculty_logged_in'):
            view_attendance()
        elif st.session_state.page == 'edit_attendance' and st.session_state.get('faculty_logged_in'):
            edit_attendance()
        elif st.session_state.page == 'analytics' and st.session_state.get('faculty_logged_in'):
            analytics()
        elif st.session_state.page == 'student_app':
            student_app()
        else:
            # Redirect to home for invalid states
            st.session_state.page = 'home'
            st.rerun()
            
    except Exception as e:
        st.error(f"Application Error: {str(e)}")
        st.info("🔄 Redirecting to home page...")
        st.session_state.page = 'home'
        if st.button("Go to Home"):
            st.rerun()

if __name__ == "__main__":
    main()