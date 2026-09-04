import { Link } from 'react-router-dom';
import Navbar from '../components/Navbar';

const NotFound = () => {
  return (
    <>
      <Navbar currentPage="" />
      <main className="container mx-auto bg-white shadow-lg rounded-lg p-8 mt-10 max-w-6xl text-center">
        <h1 className="text-6xl text-red-500 font-bold mb-4">404</h1>
        <h2 className="text-2xl text-gray-700 mb-6">Page Not Found</h2>
        <p className="text-gray-600 mb-6">Sorry, the page you're looking for doesn't exist.</p>
        <Link 
          to="/" 
          className="inline-block bg-red-500 text-white py-2 px-6 rounded-md hover:bg-red-600 transition duration-300"
        >
          Go Home
        </Link>
      </main>
    </>
  );
};

export default NotFound;
