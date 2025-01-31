import React from 'react';
import { Link } from 'react-router-dom';

const Navbar = () => {
  return (
    <nav className="bg-gray-800 p-4">
      <div className="container mx-auto flex justify-between items-center">
        {/* Logo/Title */}
        <Link to="/" className="text-white text-2xl font-bold">
          Pysage
        </Link>

        {/* Navigation Links */}
        <div className="space-x-4">
          <Link to="/" className="text-white hover:text-gray-300">
            Home
          </Link>
          <Link to="/about" className="text-white hover:text-gray-300">
            About Us
          </Link>
          <Link to="/blog" className="text-white hover:text-gray-300">
            Blog
          </Link>
          <Link to="/websocket" className="text-white hover:text-gray-300">
            Websocket
          </Link>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
