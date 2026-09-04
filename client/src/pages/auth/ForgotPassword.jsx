import { useState } from 'react';
import { Link } from 'react-router-dom';
import Navbar from '../../components/Navbar';
import ErrorAlert from '../../components/ErrorAlert';
import axios from 'axios';
import { API_URL } from '../../config/api';

const ForgotPassword = () => {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [errors, setErrors] = useState([]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setErrors([]);
    setSuccess(false);

    try {
      const response = await axios.post(`${API_URL}/api/password-reset/request`, 
        { email },
        { withCredentials: true }
      );

      if (response.data.success) {
        setSuccess(true);
        setEmail('');
      } else {
        setErrors(response.data.errors || ['Failed to send reset email']);
      }
    } catch (error) {
      setErrors([error.response?.data?.errors?.[0] || 'An error occurred. Please try again.']);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <Navbar currentPage="login" />
      <main className="container mx-auto mt-8 p-8 bg-white rounded-lg shadow-md max-w-md">
        <div className="text-center mb-6">
          <div className="inline-block p-4 bg-red-100 rounded-full mb-4">
            <i className="fas fa-lock text-red-500 text-3xl"></i>
          </div>
          <h1 className="text-3xl font-bold text-gray-800">Forgot Password?</h1>
          <p className="text-gray-600 mt-2">No worries! Enter your email and we'll send you reset instructions.</p>
        </div>

        {success ? (
          <div className="bg-green-50 border border-green-200 rounded-lg p-6 text-center">
            <i className="fas fa-check-circle text-green-500 text-4xl mb-3"></i>
            <h3 className="text-lg font-semibold text-green-800 mb-2">Email Sent!</h3>
            <p className="text-green-700 mb-4">
              If an account exists with that email, we've sent password reset instructions.
            </p>
            <p className="text-sm text-gray-600 mb-4">
              Check your inbox and spam folder for the reset link.
            </p>
            <Link 
              to="/login" 
              className="inline-block bg-red-500 text-white px-6 py-2 rounded-md hover:bg-red-600 transition"
            >
              Back to Login
            </Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit}>
            <ErrorAlert errors={errors} />

            <div className="mb-6">
              <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-2">
                Email Address
              </label>
              <div className="relative">
                <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-gray-500">
                  <i className="fas fa-envelope"></i>
                </span>
                <input
                  type="email"
                  id="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="your.email@example.com"
                  className="w-full pl-10 px-4 py-3 border rounded-md focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-red-500 transition"
                  required
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-red-500 text-white py-3 rounded-md hover:bg-red-600 focus:ring-4 focus:ring-red-300 font-medium transition duration-300 flex items-center justify-center"
            >
              {loading ? (
                <>
                  <i className="fas fa-spinner fa-spin mr-2"></i>
                  Sending...
                </>
              ) : (
                <>
                  <i className="fas fa-paper-plane mr-2"></i>
                  Send Reset Link
                </>
              )}
            </button>

            <div className="mt-6 text-center">
              <Link to="/login" className="text-red-500 hover:underline flex items-center justify-center">
                <i className="fas fa-arrow-left mr-2"></i>
                Back to Login
              </Link>
            </div>
          </form>
        )}
      </main>
    </>
  );
};

export default ForgotPassword;
