// Firebase Auth mock/wrapper (to be replaced with actual Firebase SDK if provided config)

class AuthService {
  constructor() {
    this.token = localStorage.getItem('auth_token');
    this.user = JSON.parse(localStorage.getItem('auth_user') || 'null');
  }

  // Temporary mock sign in
  async signIn(email, password) {
    // Mock login for now
    this.token = 'mock_firebase_token_12345';
    this.user = { uid: 'user1', email, role: 'admin', name: 'John Doe' };
    
    localStorage.setItem('auth_token', this.token);
    localStorage.setItem('auth_user', JSON.stringify(this.user));
    
    return this.user;
  }

  async signOut() {
    this.token = null;
    this.user = null;
    localStorage.removeItem('auth_token');
    localStorage.removeItem('auth_user');
    window.location.hash = '#/login';
  }

  isAuthenticated() {
    return !!this.token;
  }

  getToken() {
    return this.token;
  }

  getUser() {
    return this.user;
  }
}

export const auth = new AuthService();
