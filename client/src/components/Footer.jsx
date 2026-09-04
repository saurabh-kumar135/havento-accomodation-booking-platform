import { Link } from 'react-router-dom';

const Footer = () => {
  return (
    <footer className="bg-gray-800 text-white mt-16">
      <div className="container mx-auto px-4 py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          
          {}
          <div>
            <h3 className="text-lg font-bold mb-4 text-red-400">User</h3>
            <ul className="space-y-2">
              <li>
                <Link to="/favourites" className="hover:text-red-400 transition duration-300">
                  Favourites
                </Link>
              </li>
              <li>
                <Link to="/homes" className="hover:text-red-400 transition duration-300">
                  Add to Favourites
                </Link>
              </li>
              <li>
                <Link to="/bookings" className="hover:text-red-400 transition duration-300">
                  Bookings
                </Link>
              </li>
            </ul>
          </div>

          {}
          <div>
            <h3 className="text-lg font-bold mb-4 text-red-400">Host</h3>
            <ul className="space-y-2">
              <li>
                <Link to="/host/add-home" className="hover:text-red-400 transition duration-300">
                  Add Home
                </Link>
              </li>
              <li>
                <Link to="/host/host-home-list" className="hover:text-red-400 transition duration-300">
                  Manage Homes
                </Link>
              </li>
            </ul>
          </div>

          {}
          <div>
            <h3 className="text-lg font-bold mb-4 text-red-400">About</h3>
            <ul className="space-y-2">
              <li>
                <a href="#" className="hover:text-red-400 transition duration-300">
                  About Us
                </a>
              </li>
              <li>
                <a href="#" className="hover:text-red-400 transition duration-300">
                  Contact
                </a>
              </li>
              <li>
                <a href="#" className="hover:text-red-400 transition duration-300">
                  Privacy Policy
                </a>
              </li>
            </ul>
          </div>
        </div>

        {}
        <div className="border-t border-gray-700 mt-8 pt-8 text-center text-gray-400">
          <p>&copy; 2024 HavenTo. All rights reserved.</p>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
