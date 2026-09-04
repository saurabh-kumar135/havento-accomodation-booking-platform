import { useState, useEffect } from 'react';
import { useLocation, useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import Navbar from '../../components/Navbar';
import ErrorAlert from '../../components/ErrorAlert';
import axios from 'axios';
import { API_URL } from '../../config/api';

const VerifyEmail = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { checkSessionStatus } = useAuth();
  const { email, firstName } = location.state || {};

  const [otp, setOtp] = useState(['', '', '', '', '', '']);
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState([]);
  const [timeLeft, setTimeLeft] = useState(300); 
  const [canResend, setCanResend] = useState(false);

  useEffect(() => {
    if (!email) {
      navigate('/signup');
    }
  }, [email, navigate]);

  useEffect(() => {
    if (timeLeft === 0) {
      setCanResend(true);
      return;
    }

    const timer = setInterval(() => {
      setTimeLeft((prev) => prev - 1);
    }, 1000);

    return () => clearInterval(timer);
  }, [timeLeft]);

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const handleChange = (index, value) => {
    if (!/^\d*$/.test(value)) return; 

    const newOtp = [...otp];
    newOtp[index] = value;
    setOtp(newOtp);

    if (value && index < 5) {
      document.getElementById(`otp-${index + 1}`).focus();
    }

    if (newOtp.every((digit) => digit !== '') && index === 5) {
      handleVerify(newOtp.join(''));
    }
  };

  const handleKeyDown = (index, e) => {
    if (e.key === 'Backspace' && !otp[index] && index > 0) {
      document.getElementById(`otp-${index - 1}`).focus();
    }
  };

  const handlePaste = (e) => {
    e.preventDefault();
    const pastedData = e.clipboardData.getData('text').slice(0, 6);
    if (!/^\d+$/.test(pastedData)) return;

    const newOtp = pastedData.split('');
    while (newOtp.length < 6) newOtp.push('');
    setOtp(newOtp);

    if (pastedData.length === 6) {
      handleVerify(pastedData);
    }
  };

  const handleVerify = async (otpCode) => {
    setLoading(true);
    setErrors([]);

    try {
      const response = await axios.post(
        `${API_URL}/api/verify-email/verify-otp`,
        { email, otp: otpCode || otp.join('') },
        { withCredentials: true }
      );

      if (response.data.success) {
        
        await checkSessionStatus();
        
        navigate('/');
      } else {
        setErrors(response.data.errors || ['Verification failed']);
      }
    } catch (error) {
      setErrors([error.response?.data?.errors?.[0] || 'An error occurred']);
    } finally {
      setLoading(false);
    }
  };

  const handleResend = async () => {
    setLoading(true);
    setErrors([]);

    try {
      const response = await axios.post(
        `${API_URL}/api/verify-email/resend-otp`,
        { email },
        { withCredentials: true }
      );

      if (response.data.success) {
        setTimeLeft(300); 
        setCanResend(false);
        setOtp(['', '', '', '', '', '']);
        document.getElementById('otp-0').focus();
      } else {
        setErrors(response.data.errors || ['Failed to resend code']);
      }
    } catch (error) {
      setErrors([error.response?.data?.errors?.[0] || 'An error occurred']);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <Navbar currentPage="signup" />
      <main className="container mx-auto mt-8 p-8 bg-white rounded-lg shadow-md max-w-md">
        <div className="text-center mb-6">
          <div className="inline-block p-4 bg-purple-100 rounded-full mb-4">
            <i className="fas fa-envelope-open-text text-purple-500 text-3xl"></i>
          </div>
          <h1 className="text-3xl font-bold text-gray-800">Verify Your Email</h1>
          <p className="text-gray-600 mt-2">
            We've sent a 6-digit code to
          </p>
          <p className="text-purple-600 font-semibold">{email}</p>
        </div>

        <ErrorAlert errors={errors} />

        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-3 text-center">
            Enter Verification Code
          </label>
          <div className="flex justify-center gap-2" onPaste={handlePaste}>
            {otp.map((digit, index) => (
              <input
                key={index}
                id={`otp-${index}`}
                type="text"
                maxLength="1"
                value={digit}
                onChange={(e) => handleChange(index, e.target.value)}
                onKeyDown={(e) => handleKeyDown(index, e)}
                className="w-12 h-14 text-center text-2xl font-bold border-2 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-purple-500 transition"
                disabled={loading}
              />
            ))}
          </div>
        </div>

        <div className="text-center mb-6">
          {timeLeft > 0 ? (
            <p className="text-gray-600">
              Code expires in{' '}
              <span className="font-semibold text-purple-600">{formatTime(timeLeft)}</span>
            </p>
          ) : (
            <p className="text-red-500 font-semibold">Code expired!</p>
          )}
        </div>

        <button
          onClick={() => handleVerify()}
          disabled={loading || otp.some((d) => !d)}
          className="w-full bg-purple-500 text-white py-3 rounded-md hover:bg-purple-600 focus:ring-4 focus:ring-purple-300 font-medium transition duration-300 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center mb-4"
        >
          {loading ? (
            <>
              <i className="fas fa-spinner fa-spin mr-2"></i>
              Verifying...
            </>
          ) : (
            <>
              <i className="fas fa-check mr-2"></i>
              Verify Email
            </>
          )}
        </button>

        <div className="text-center">
          {canResend || timeLeft === 0 ? (
            <button
              onClick={handleResend}
              disabled={loading}
              className="text-purple-500 hover:underline font-medium"
            >
              <i className="fas fa-redo mr-2"></i>
              Resend Code
            </button>
          ) : (
            <p className="text-gray-500 text-sm">
              Didn't receive the code? Wait {formatTime(timeLeft)} to resend
            </p>
          )}
        </div>

        <div className="mt-6 text-center">
          <Link to="/signup" className="text-gray-600 hover:underline flex items-center justify-center">
            <i className="fas fa-arrow-left mr-2"></i>
            Back to Signup
          </Link>
        </div>
      </main>
    </>
  );
};

export default VerifyEmail;
