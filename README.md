# **Smart Attendance Management System**

## **Overview**
A complete web-based attendance management solution that combines **QR code technology** with **GPS location verification** to ensure accurate and secure attendance tracking for educational institutions.  
Built with **Streamlit**, this system provides separate interfaces for **administrators**, **faculty members**, and **students**.

---

## **Table of Contents**

- **Features**  
- **System Architecture**  
- **Installation & Setup**  
- **User Guide**  
- **Database Schema**  
- **API Reference**  
- **Security**  
- **Configuration**  
- **Troubleshooting**  
- **Contributing**  
- **License**  

---

## **Features**

### **Administrative Features**
- **Complete User Management**: Create, modify, and deactivate faculty accounts  
- **System-wide Analytics**: Comprehensive attendance statistics and trends  
- **Announcement System**: Broadcast messages to faculty and students  
- **Multi-role Access Control**: Separate permissions for administrators and faculty  
- **Data Export**: Export attendance records in CSV format  
- **Real-time Dashboard**: Live attendance monitoring and statistics  

### **Faculty Features**
- **QR Code Generation**: Create location and time-bound QR codes for classes  
- **Attendance Monitoring**: Real-time view of student attendance  
- **Record Management**: Edit and update attendance records with audit trails  
- **Subject Management**: Handle multiple subjects and class periods  
- **Analytics Dashboard**: Class-specific attendance reports and visualizations  
- **Flexible Scheduling**: Support for multiple periods and custom time slots  

### **Student Features**
- **QR Code Scanning**: Upload QR code images for attendance marking  
- **GPS Verification**: Automatic location validation to prevent proxy attendance  
- **Instant Feedback**: Real-time confirmation of attendance submission  
- **Duplicate Prevention**: System blocks multiple entries for same session  
- **Simple Interface**: User-friendly mobile-optimized interface  

### **Technical Features**
- **Persistent Database**: SQLite-based data storage with relationship integrity  
- **Session Management**: Secure user sessions with role-based access  
- **Image Processing**: Advanced QR code reading with OpenCV  
- **Data Visualization**: Interactive charts and graphs using Plotly  
- **Responsive Design**: Works on desktop and mobile devices  
- **Error Handling**: Comprehensive error management and user feedback  

---

## **System Architecture**

### **Technology Stack**
- **Frontend**: Streamlit (Web Interface)  
- **Backend**: Python 3.7+  
- **Database**: SQLite3 with foreign key constraints  
- **QR Processing**: qrcode library with PIL image handling  
- **Computer Vision**: OpenCV for QR code detection and reading  
- **Data Analysis**: Pandas for data manipulation and analysis  
- **Visualization**: Plotly for interactive charts and graphs  
- **Security**: SHA-256 password hashing  

---

### **Administrator Workflow**

#### **Login Process**
1. Navigate to faculty login page  
2. Enter admin credentials  
3. Access admin dashboard  

#### **User Management**
- Add new faculty members  
- Assign subjects and departments  
- Manage user permissions  

#### **System Monitoring**
- View real-time attendance statistics  
- Monitor system usage patterns  
- Generate comprehensive reports  

#### **Announcement Management**
- Create system-wide announcements  
- Target specific user groups  
- Set priority levels  

---

### **Faculty Workflow**

#### **Class Preparation**
1. Login to faculty dashboard  
2. Select "Generate QR Code"  
3. Enter subject and period information  
4. Set classroom GPS coordinates  
5. Choose QR code validity period  

#### **Attendance Collection**
- Display generated QR code to students  
- Monitor real-time attendance submissions  
- Handle special cases (late arrivals, technical issues)  

#### **Record Management**
- Review attendance records  
- Edit entries with proper documentation  
- Export data for external use  

---

### **Student Workflow**

#### **Attendance Marking**
1. Access student portal  
2. Capture or screenshot teacher's QR code  
3. Upload QR code image  
4. Enter personal details (name, roll number)  
5. Submit attendance  

#### **Location Verification**
- System automatically checks GPS coordinates  
- Validates proximity to classroom  
- Confirms or rejects submission  
