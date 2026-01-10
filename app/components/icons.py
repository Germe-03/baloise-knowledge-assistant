"""
KMU Knowledge Assistant - CSS-basierte Icons
Apple-Style SVG Icons (SF Symbols inspiriert)
"""

import streamlit as st

# CSS fuer Icon-Buttons
ICON_BUTTON_CSS = """
<style>
/* Icon Button Base Style */
.icon-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    border-radius: 8px;
    border: none;
    background: #f5f5f7;
    cursor: pointer;
    transition: all 0.2s ease;
    color: #1d1d1f;
}

.icon-btn:hover {
    background: #e8e8ed;
    transform: scale(1.05);
}

.icon-btn.primary {
    background: #007aff;
    color: white;
}

.icon-btn.primary:hover {
    background: #0056b3;
}

.icon-btn.success {
    background: #34c759;
    color: white;
}

.icon-btn.danger {
    background: #ff3b30;
    color: white;
}

/* Status Dots */
.status-dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    margin-right: 8px;
}

.status-dot.active { background: #34c759; }
.status-dot.inactive { background: #ff3b30; }
.status-dot.warning { background: #ff9500; }
.status-dot.neutral { background: #8e8e93; }

/* Icon with Label */
.icon-label {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 14px;
    color: #1d1d1f;
}

.icon-label svg {
    flex-shrink: 0;
}

/* Badge Style */
.badge {
    display: inline-flex;
    align-items: center;
    padding: 4px 10px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: 500;
}

.badge.success {
    background: #d1f2d9;
    color: #1d7a3c;
}

.badge.error {
    background: #fdd;
    color: #c41e3a;
}

.badge.warning {
    background: #fff3cd;
    color: #856404;
}

.badge.info {
    background: #e7f3ff;
    color: #0066cc;
}

/* Feedback Buttons Container */
.feedback-btns {
    display: flex;
    gap: 8px;
}

.feedback-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 36px;
    height: 36px;
    border-radius: 10px;
    border: 1px solid #e5e5e5;
    background: white;
    cursor: pointer;
    transition: all 0.15s ease;
}

.feedback-btn:hover {
    background: #f5f5f7;
    border-color: #d1d1d6;
}

.feedback-btn.positive:hover {
    background: #d1f2d9;
    border-color: #34c759;
}

.feedback-btn.negative:hover {
    background: #fdd;
    border-color: #ff3b30;
}

.feedback-btn.active.positive {
    background: #34c759;
    border-color: #34c759;
    color: white;
}

.feedback-btn.active.negative {
    background: #ff3b30;
    border-color: #ff3b30;
    color: white;
}

/* Section Headers with Icon */
.section-header {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 16px;
}

.section-header svg {
    color: #8e8e93;
}

.section-header h3 {
    margin: 0;
    font-size: 17px;
    font-weight: 600;
    color: #1d1d1f;
}
</style>
"""

# SVG Icons (Apple SF Symbols Style - Clean, Minimal)
ICONS = {
    # Feedback
    "thumbs_up": '''<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M7 22V11M2 13V20C2 21.1 2.9 22 4 22H17.4C18.6 22 19.6 21.2 19.9 20L21.6 13C22 11.6 21 10.2 19.5 10.2H14.5V5.8C14.5 4.3 13.3 3 11.8 3L7 11" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>''',

    "thumbs_down": '''<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M17 2V13M22 11V4C22 2.9 21.1 2 20 2H6.6C5.4 2 4.4 2.8 4.1 4L2.4 11C2 12.4 3 13.8 4.5 13.8H9.5V18.2C9.5 19.7 10.7 21 12.2 21L17 13" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>''',

    # Status
    "check": '''<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <polyline points="20 6 9 17 4 12" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>''',

    "check_circle": '''<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <circle cx="12" cy="12" r="10"/>
        <path d="M8 12L11 15L16 9" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>''',

    "x": '''<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M18 6L6 18M6 6L18 18" stroke-linecap="round"/>
    </svg>''',

    "x_circle": '''<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <circle cx="12" cy="12" r="10"/>
        <path d="M15 9L9 15M9 9L15 15" stroke-linecap="round"/>
    </svg>''',

    "alert": '''<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M12 9V13M12 17H12.01M10.29 3.86L1.82 18C1.64 18.3 1.55 18.64 1.55 19C1.55 19.75 2.04 20.44 2.73 20.72C2.97 20.82 3.24 20.88 3.51 20.88H20.49C21.31 20.88 22 20.19 22 19.37C22 19.01 21.89 18.66 21.68 18.37L13.21 3.86C12.65 2.87 11.35 2.87 10.29 3.86Z" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>''',

    "info": '''<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <circle cx="12" cy="12" r="10"/>
        <path d="M12 16V12M12 8H12.01" stroke-linecap="round"/>
    </svg>''',

    # Actions
    "plus": '''<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M12 5V19M5 12H19" stroke-linecap="round"/>
    </svg>''',

    "minus": '''<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M5 12H19" stroke-linecap="round"/>
    </svg>''',

    "edit": '''<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M11 4H4C3.46957 4 2.96086 4.21071 2.58579 4.58579C2.21071 4.96086 2 5.46957 2 6V20C2 20.5304 2.21071 21.0391 2.58579 21.4142C2.96086 21.7893 3.46957 22 4 22H18C18.5304 22 19.0391 21.7893 19.4142 21.4142C19.7893 21.0391 20 20.5304 20 20V13" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M18.5 2.50001C18.8978 2.10219 19.4374 1.87869 20 1.87869C20.5626 1.87869 21.1022 2.10219 21.5 2.50001C21.8978 2.89784 22.1213 3.43739 22.1213 4.00001C22.1213 4.56262 21.8978 5.10219 21.5 5.50001L12 15L8 16L9 12L18.5 2.50001Z" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>''',

    "trash": '''<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M3 6H5H21" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M8 6V4C8 3.46957 8.21071 2.96086 8.58579 2.58579C8.96086 2.21071 9.46957 2 10 2H14C14.5304 2 15.0391 2.21071 15.4142 2.58579C15.7893 2.96086 16 3.46957 16 4V6M19 6V20C19 20.5304 18.7893 21.0391 18.4142 21.4142C18.0391 21.7893 17.5304 22 17 22H7C6.46957 22 5.96086 21.7893 5.58579 21.4142C5.21071 21.0391 5 20.5304 5 20V6H19Z" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>''',

    "refresh": '''<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M1 4V10H7" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M23 20V14H17" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M20.49 9C19.9828 7.56678 19.1209 6.28543 17.9845 5.27542C16.8482 4.26541 15.4745 3.55976 13.9917 3.22426C12.5089 2.88875 10.9652 2.93434 9.50481 3.35677C8.04437 3.77921 6.71475 4.56471 5.64 5.64L1 10M23 14L18.36 18.36C17.2853 19.4353 15.9556 20.2208 14.4952 20.6432C13.0348 21.0657 11.4911 21.1113 10.0083 20.7757C8.52547 20.4402 7.1518 19.7346 6.01547 18.7246C4.87913 17.7146 4.01717 16.4332 3.51 15" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>''',

    "upload": '''<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M21 15V19C21 19.5304 20.7893 20.0391 20.4142 20.4142C20.0391 20.7893 19.5304 21 19 21H5C4.46957 21 3.96086 20.7893 3.58579 20.4142C3.21071 20.0391 3 19.5304 3 19V15" stroke-linecap="round" stroke-linejoin="round"/>
        <polyline points="17 8 12 3 7 8" stroke-linecap="round" stroke-linejoin="round"/>
        <line x1="12" y1="3" x2="12" y2="15" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>''',

    "download": '''<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M21 15V19C21 19.5304 20.7893 20.0391 20.4142 20.4142C20.0391 20.7893 19.5304 21 19 21H5C4.46957 21 3.96086 20.7893 3.58579 20.4142C3.21071 20.0391 3 19.5304 3 19V15" stroke-linecap="round" stroke-linejoin="round"/>
        <polyline points="7 10 12 15 17 10" stroke-linecap="round" stroke-linejoin="round"/>
        <line x1="12" y1="15" x2="12" y2="3" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>''',

    # Navigation
    "search": '''<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <circle cx="11" cy="11" r="8"/>
        <path d="M21 21L16.65 16.65" stroke-linecap="round"/>
    </svg>''',

    "home": '''<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M3 9L12 2L21 9V20C21 20.5304 20.7893 21.0391 20.4142 21.4142C20.0391 21.7893 19.5304 22 19 22H5C4.46957 22 3.96086 21.7893 3.58579 21.4142C3.21071 21.0391 3 20.5304 3 20V9Z" stroke-linecap="round" stroke-linejoin="round"/>
        <polyline points="9 22 9 12 15 12 15 22" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>''',

    "settings": '''<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <circle cx="12" cy="12" r="3"/>
        <path d="M19.4 15C19.2669 15.3016 19.2272 15.6362 19.286 15.9606C19.3448 16.285 19.4995 16.5843 19.73 16.82L19.79 16.88C19.976 17.0657 20.1235 17.2863 20.2241 17.5291C20.3248 17.7719 20.3766 18.0322 20.3766 18.295C20.3766 18.5578 20.3248 18.8181 20.2241 19.0609C20.1235 19.3037 19.976 19.5243 19.79 19.71C19.6043 19.896 19.3837 20.0435 19.1409 20.1441C18.8981 20.2448 18.6378 20.2966 18.375 20.2966C18.1122 20.2966 17.8519 20.2448 17.6091 20.1441C17.3663 20.0435 17.1457 19.896 16.96 19.71L16.9 19.65C16.6643 19.4195 16.365 19.2648 16.0406 19.206C15.7162 19.1472 15.3816 19.1869 15.08 19.32C14.7842 19.4468 14.532 19.6572 14.3543 19.9255C14.1766 20.1938 14.0813 20.5082 14.08 20.83V21C14.08 21.5304 13.8693 22.0391 13.4942 22.4142C13.1191 22.7893 12.6104 23 12.08 23C11.5496 23 11.0409 22.7893 10.6658 22.4142C10.2907 22.0391 10.08 21.5304 10.08 21V20.91C10.0723 20.579 9.96512 20.258 9.77251 19.9887C9.5799 19.7194 9.31074 19.5143 9 19.4C8.69838 19.2669 8.36381 19.2272 8.03941 19.286C7.71502 19.3448 7.41568 19.4995 7.18 19.73L7.12 19.79C6.93425 19.976 6.71368 20.1235 6.47088 20.2241C6.22808 20.3248 5.96783 20.3766 5.705 20.3766C5.44217 20.3766 5.18192 20.3248 4.93912 20.2241C4.69632 20.1235 4.47575 19.976 4.29 19.79C4.10405 19.6043 3.95653 19.3837 3.85588 19.1409C3.75523 18.8981 3.70343 18.6378 3.70343 18.375C3.70343 18.1122 3.75523 17.8519 3.85588 17.6091C3.95653 17.3663 4.10405 17.1457 4.29 16.96L4.35 16.9C4.58054 16.6643 4.73519 16.365 4.794 16.0406C4.85282 15.7162 4.81312 15.3816 4.68 15.08C4.55324 14.7842 4.34276 14.532 4.07447 14.3543C3.80618 14.1766 3.49179 14.0813 3.17 14.08H3C2.46957 14.08 1.96086 13.8693 1.58579 13.4942C1.21071 13.1191 1 12.6104 1 12.08C1 11.5496 1.21071 11.0409 1.58579 10.6658C1.96086 10.2907 2.46957 10.08 3 10.08H3.09C3.42099 10.0723 3.742 9.96512 4.0113 9.77251C4.28059 9.5799 4.48572 9.31074 4.6 9C4.73312 8.69838 4.77282 8.36381 4.714 8.03941C4.65519 7.71502 4.50054 7.41568 4.27 7.18L4.21 7.12C4.02405 6.93425 3.87653 6.71368 3.77588 6.47088C3.67523 6.22808 3.62343 5.96783 3.62343 5.705C3.62343 5.44217 3.67523 5.18192 3.77588 4.93912C3.87653 4.69632 4.02405 4.47575 4.21 4.29C4.39575 4.10405 4.61632 3.95653 4.85912 3.85588C5.10192 3.75523 5.36217 3.70343 5.625 3.70343C5.88783 3.70343 6.14808 3.75523 6.39088 3.85588C6.63368 3.95653 6.85425 4.10405 7.04 4.29L7.1 4.35C7.33568 4.58054 7.63502 4.73519 7.95941 4.794C8.28381 4.85282 8.61838 4.81312 8.92 4.68H9C9.29577 4.55324 9.54802 4.34276 9.72569 4.07447C9.90337 3.80618 9.99872 3.49179 10 3.17V3C10 2.46957 10.2107 1.96086 10.5858 1.58579C10.9609 1.21071 11.4696 1 12 1C12.5304 1 13.0391 1.21071 13.4142 1.58579C13.7893 1.96086 14 2.46957 14 3V3.09C14.0013 3.41179 14.0966 3.72618 14.2743 3.99447C14.452 4.26276 14.7042 4.47324 15 4.6C15.3016 4.73312 15.6362 4.77282 15.9606 4.714C16.285 4.65519 16.5843 4.50054 16.82 4.27L16.88 4.21C17.0657 4.02405 17.2863 3.87653 17.5291 3.77588C17.7719 3.67523 18.0322 3.62343 18.295 3.62343C18.5578 3.62343 18.8181 3.67523 19.0609 3.77588C19.3037 3.87653 19.5243 4.02405 19.71 4.21C19.896 4.39575 20.0435 4.61632 20.1441 4.85912C20.2448 5.10192 20.2966 5.36217 20.2966 5.625C20.2966 5.88783 20.2448 6.14808 20.1441 6.39088C20.0435 6.63368 19.896 6.85425 19.71 7.04L19.65 7.1C19.4195 7.33568 19.2648 7.63502 19.206 7.95941C19.1472 8.28381 19.1869 8.61838 19.32 8.92V9C19.4468 9.29577 19.6572 9.54802 19.9255 9.72569C20.1938 9.90337 20.5082 9.99872 20.83 10H21C21.5304 10 22.0391 10.2107 22.4142 10.5858C22.7893 10.9609 23 11.4696 23 12C23 12.5304 22.7893 13.0391 22.4142 13.4142C22.0391 13.7893 21.5304 14 21 14H20.91C20.5882 14.0013 20.2738 14.0966 20.0055 14.2743C19.7372 14.452 19.5268 14.7042 19.4 15Z" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>''',

    # Users
    "user": '''<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M20 21V19C20 17.9391 19.5786 16.9217 18.8284 16.1716C18.0783 15.4214 17.0609 15 16 15H8C6.93913 15 5.92172 15.4214 5.17157 16.1716C4.42143 16.9217 4 17.9391 4 19V21" stroke-linecap="round" stroke-linejoin="round"/>
        <circle cx="12" cy="7" r="4" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>''',

    "users": '''<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M17 21V19C17 17.9391 16.5786 16.9217 15.8284 16.1716C15.0783 15.4214 14.0609 15 13 15H5C3.93913 15 2.92172 15.4214 2.17157 16.1716C1.42143 16.9217 1 17.9391 1 19V21" stroke-linecap="round" stroke-linejoin="round"/>
        <circle cx="9" cy="7" r="4" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M23 21V19C22.9993 18.1137 22.7044 17.2528 22.1614 16.5523C21.6184 15.8519 20.8581 15.3516 20 15.13" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M16 3.13C16.8604 3.35031 17.623 3.85071 18.1676 4.55232C18.7122 5.25392 19.0078 6.11683 19.0078 7.005C19.0078 7.89318 18.7122 8.75608 18.1676 9.45769C17.623 10.1593 16.8604 10.6597 16 10.88" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>''',

    # Files & Folders
    "folder": '''<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M22 19C22 19.5304 21.7893 20.0391 21.4142 20.4142C21.0391 20.7893 20.5304 21 20 21H4C3.46957 21 2.96086 20.7893 2.58579 20.4142C2.21071 20.0391 2 19.5304 2 19V5C2 4.46957 2.21071 3.96086 2.58579 3.58579C2.96086 3.21071 3.46957 3 4 3H9L11 6H20C20.5304 6 21.0391 6.21071 21.4142 6.58579C21.7893 6.96086 22 7.46957 22 8V19Z" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>''',

    "file": '''<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M13 2H6C5.46957 2 4.96086 2.21071 4.58579 2.58579C4.21071 2.96086 4 3.46957 4 4V20C4 20.5304 4.21071 21.0391 4.58579 21.4142C4.96086 21.7893 5.46957 22 6 22H18C18.5304 22 19.0391 21.7893 19.4142 21.4142C19.7893 21.0391 20 20.5304 20 20V9L13 2Z" stroke-linecap="round" stroke-linejoin="round"/>
        <polyline points="13 2 13 9 20 9" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>''',

    "book": '''<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M4 19.5C4 18.837 4.26339 18.2011 4.73223 17.7322C5.20107 17.2634 5.83696 17 6.5 17H20" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M6.5 2H20V22H6.5C5.83696 22 5.20107 21.7366 4.73223 21.2678C4.26339 20.7989 4 20.163 4 19.5V4.5C4 3.83696 4.26339 3.20107 4.73223 2.73223C5.20107 2.26339 5.83696 2 6.5 2Z" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>''',

    # Security
    "lock": '''<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <rect x="3" y="11" width="18" height="11" rx="2" ry="2" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M7 11V7C7 5.67392 7.52678 4.40215 8.46447 3.46447C9.40215 2.52678 10.6739 2 12 2C13.3261 2 14.5979 2.52678 15.5355 3.46447C16.4732 4.40215 17 5.67392 17 7V11" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>''',

    "unlock": '''<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <rect x="3" y="11" width="18" height="11" rx="2" ry="2" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M7 11V7C7 5.67392 7.52678 4.40215 8.46447 3.46447C9.40215 2.52678 10.6739 2 12 2C13.3261 2 14.5979 2.52678 15.5355 3.46447C16.4732 4.40215 17 5.67392 17 7" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>''',

    # Communication
    "chat": '''<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M21 15C21 15.5304 20.7893 16.0391 20.4142 16.4142C20.0391 16.7893 19.5304 17 19 17H7L3 21V5C3 4.46957 3.21071 3.96086 3.58579 3.58579C3.96086 3.21071 4.46957 3 5 3H19C19.5304 3 20.0391 3.21071 20.4142 3.58579C20.7893 3.96086 21 4.46957 21 5V15Z" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>''',

    "mail": '''<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M4 4H20C21.1 4 22 4.9 22 6V18C22 19.1 21.1 20 20 20H4C2.9 20 2 19.1 2 18V6C2 4.9 2.9 4 4 4Z" stroke-linecap="round" stroke-linejoin="round"/>
        <polyline points="22,6 12,13 2,6" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>''',

    # Data
    "chart": '''<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <line x1="18" y1="20" x2="18" y2="10" stroke-linecap="round" stroke-linejoin="round"/>
        <line x1="12" y1="20" x2="12" y2="4" stroke-linecap="round" stroke-linejoin="round"/>
        <line x1="6" y1="20" x2="6" y2="14" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>''',

    "list": '''<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <line x1="8" y1="6" x2="21" y2="6" stroke-linecap="round" stroke-linejoin="round"/>
        <line x1="8" y1="12" x2="21" y2="12" stroke-linecap="round" stroke-linejoin="round"/>
        <line x1="8" y1="18" x2="21" y2="18" stroke-linecap="round" stroke-linejoin="round"/>
        <line x1="3" y1="6" x2="3.01" y2="6" stroke-linecap="round" stroke-linejoin="round"/>
        <line x1="3" y1="12" x2="3.01" y2="12" stroke-linecap="round" stroke-linejoin="round"/>
        <line x1="3" y1="18" x2="3.01" y2="18" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>''',

    # Misc
    "calendar": '''<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <rect x="3" y="4" width="18" height="18" rx="2" ry="2" stroke-linecap="round" stroke-linejoin="round"/>
        <line x1="16" y1="2" x2="16" y2="6" stroke-linecap="round" stroke-linejoin="round"/>
        <line x1="8" y1="2" x2="8" y2="6" stroke-linecap="round" stroke-linejoin="round"/>
        <line x1="3" y1="10" x2="21" y2="10" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>''',

    "clock": '''<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <circle cx="12" cy="12" r="10"/>
        <polyline points="12 6 12 12 16 14" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>''',

    "logout": '''<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M9 21H5C4.46957 21 3.96086 20.7893 3.58579 20.4142C3.21071 20.0391 3 19.5304 3 19V5C3 4.46957 3.21071 3.96086 3.58579 3.58579C3.96086 3.21071 4.46957 3 5 3H9" stroke-linecap="round" stroke-linejoin="round"/>
        <polyline points="16 17 21 12 16 7" stroke-linecap="round" stroke-linejoin="round"/>
        <line x1="21" y1="12" x2="9" y2="12" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>''',

    "building": '''<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <rect x="4" y="2" width="16" height="20" rx="2" ry="2" stroke-linecap="round" stroke-linejoin="round"/>
        <line x1="9" y1="22" x2="9" y2="18" stroke-linecap="round" stroke-linejoin="round"/>
        <line x1="15" y1="22" x2="15" y2="18" stroke-linecap="round" stroke-linejoin="round"/>
        <line x1="8" y1="6" x2="8" y2="6.01" stroke-linecap="round" stroke-linejoin="round"/>
        <line x1="12" y1="6" x2="12" y2="6.01" stroke-linecap="round" stroke-linejoin="round"/>
        <line x1="16" y1="6" x2="16" y2="6.01" stroke-linecap="round" stroke-linejoin="round"/>
        <line x1="8" y1="10" x2="8" y2="10.01" stroke-linecap="round" stroke-linejoin="round"/>
        <line x1="12" y1="10" x2="12" y2="10.01" stroke-linecap="round" stroke-linejoin="round"/>
        <line x1="16" y1="10" x2="16" y2="10.01" stroke-linecap="round" stroke-linejoin="round"/>
        <line x1="8" y1="14" x2="8" y2="14.01" stroke-linecap="round" stroke-linejoin="round"/>
        <line x1="12" y1="14" x2="12" y2="14.01" stroke-linecap="round" stroke-linejoin="round"/>
        <line x1="16" y1="14" x2="16" y2="14.01" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>''',
}


def icon(name: str, size: int = 20, color: str = "currentColor") -> str:
    """
    Gibt ein SVG-Icon als HTML-String zurueck.

    Args:
        name: Icon-Name (z.B. "thumbs_up", "check", etc.)
        size: Groesse in Pixel
        color: CSS-Farbe

    Returns:
        HTML-String mit dem SVG-Icon
    """
    svg = ICONS.get(name, ICONS.get("file"))
    if size != 20:
        svg = svg.replace('width="20"', f'width="{size}"')
        svg = svg.replace('height="20"', f'height="{size}"')
    if color != "currentColor":
        svg = svg.replace('stroke="currentColor"', f'stroke="{color}"')
    return f'<span style="display:inline-flex;align-items:center;vertical-align:middle;line-height:1;">{svg}</span>'


def icon_text(icon_name: str, text: str, size: int = 20, color: str = "currentColor", gap: int = 8) -> str:
    """Icon mit Text daneben."""
    return f'''<span style="display:inline-flex;align-items:center;gap:{gap}px;">
        {icon(icon_name, size, color)}
        <span>{text}</span>
    </span>'''


def status_dot(status: str) -> str:
    """Farbiger Status-Punkt."""
    colors = {
        "active": "#34c759",
        "success": "#34c759",
        "inactive": "#ff3b30",
        "error": "#ff3b30",
        "warning": "#ff9500",
        "neutral": "#8e8e93",
        "info": "#007aff",
    }
    color = colors.get(status, colors["neutral"])
    return f'<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:{color};margin-right:8px;"></span>'


def badge(text: str, variant: str = "neutral") -> str:
    """Badge mit Text."""
    colors = {
        "success": ("background:#d1f2d9;color:#1d7a3c;", ""),
        "error": ("background:#fdd;color:#c41e3a;", ""),
        "warning": ("background:#fff3cd;color:#856404;", ""),
        "info": ("background:#e7f3ff;color:#0066cc;", ""),
        "neutral": ("background:#f5f5f7;color:#1d1d1f;", ""),
    }
    style, _ = colors.get(variant, colors["neutral"])
    return f'<span style="display:inline-flex;align-items:center;padding:4px 10px;border-radius:12px;font-size:12px;font-weight:500;{style}">{text}</span>'


def inject_icon_css():
    """Injiziert das Icon-CSS in Streamlit."""
    st.markdown(ICON_BUTTON_CSS, unsafe_allow_html=True)


def render_icon(name: str, size: int = 20, color: str = "#1d1d1f"):
    """Rendert ein Icon direkt in Streamlit."""
    st.markdown(icon(name, size, color), unsafe_allow_html=True)


def render_icon_text(icon_name: str, text: str, size: int = 20):
    """Rendert Icon mit Text in Streamlit."""
    st.markdown(icon_text(icon_name, text, size), unsafe_allow_html=True)


def render_status(status: str, text: str):
    """Rendert Status-Punkt mit Text."""
    st.markdown(f'{status_dot(status)}<span>{text}</span>', unsafe_allow_html=True)


def render_badge(text: str, variant: str = "neutral"):
    """Rendert ein Badge."""
    st.markdown(badge(text, variant), unsafe_allow_html=True)
