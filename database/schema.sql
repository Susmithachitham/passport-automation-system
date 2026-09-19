CREATE DATABASE IF NOT EXISTS passport_automation
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE passport_automation;

CREATE TABLE IF NOT EXISTS users (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(120) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    address TEXT NOT NULL,
    role ENUM('applicant', 'officer', 'police', 'admin') NOT NULL DEFAULT 'applicant',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS applications (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    application_id VARCHAR(32) NOT NULL UNIQUE,
    applicant_id INT UNSIGNED NOT NULL,
    application_type ENUM('NEW', 'RENEWAL', 'REISSUE') NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'DRAFT',
    personal_details JSON NULL,
    address_details JSON NULL,
    family_details JSON NULL,
    passport_details JSON NULL,
    submitted_at TIMESTAMP NULL,
    forwarded_by_id INT UNSIGNED NULL,
    forwarded_at TIMESTAMP NULL,
    rejected_by_id INT UNSIGNED NULL,
    rejection_reason TEXT NULL,
    rejected_at TIMESTAMP NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_applications_user FOREIGN KEY (applicant_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS documents (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    application_id INT UNSIGNED NOT NULL,
    document_type VARCHAR(80) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    stored_filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    mime_type VARCHAR(80) NOT NULL,
    file_size INT NOT NULL DEFAULT 0,
    verification_status VARCHAR(30) NOT NULL DEFAULT 'PENDING',
    rejection_reason TEXT NULL,
    uploaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    verified_at TIMESTAMP NULL,
    verified_by_id INT UNSIGNED NULL,
    verification_remarks TEXT NULL,
    CONSTRAINT fk_documents_application FOREIGN KEY (application_id) REFERENCES applications(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS interviews (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    application_id INT UNSIGNED NOT NULL,
    officer_id INT UNSIGNED NOT NULL,
    scheduled_date DATE NOT NULL,
    scheduled_time TIME NOT NULL,
    location VARCHAR(255) NOT NULL,
    interview_mode VARCHAR(30) NOT NULL DEFAULT 'IN_PERSON',
    status VARCHAR(30) NOT NULL DEFAULT 'SCHEDULED',
    officer_remarks TEXT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_interviews_application FOREIGN KEY (application_id) REFERENCES applications(id) ON DELETE CASCADE,
    CONSTRAINT fk_interviews_officer FOREIGN KEY (officer_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS payments (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    application_id INT UNSIGNED NOT NULL,
    transaction_id VARCHAR(40) NOT NULL UNIQUE,
    amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    payment_method VARCHAR(40) NOT NULL,
    payment_status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    paid_at TIMESTAMP NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_payments_application FOREIGN KEY (application_id) REFERENCES applications(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS police_verifications (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    application_id INT UNSIGNED NOT NULL UNIQUE,
    police_officer_id INT UNSIGNED NOT NULL,
    verification_status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    verification_date TIMESTAMP NULL,
    address_verified BOOLEAN NULL,
    identity_verified BOOLEAN NULL,
    applicant_found BOOLEAN NULL,
    criminal_record_found BOOLEAN NULL,
    remarks TEXT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_police_verifications_application FOREIGN KEY (application_id) REFERENCES applications(id) ON DELETE CASCADE,
    CONSTRAINT fk_police_verifications_officer FOREIGN KEY (police_officer_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS passports (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    application_id INT UNSIGNED NOT NULL UNIQUE,
    passport_number VARCHAR(32) NOT NULL UNIQUE,
    issue_date DATE NOT NULL,
    expiry_date DATE NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_passports_application FOREIGN KEY (application_id) REFERENCES applications(id) ON DELETE CASCADE
);
