import { useState, useEffect } from 'react';
import { getFavourites, removeFromFavourite } from '../../services/api';
import Navbar from '../../components/Navbar';
import HomeCard from '../../components/HomeCard';

const FavouriteList = () => {
  const [favourites, setFavourites] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchFavourites();
  }, []);

  const fetchFavourites = async () => {
    try {
      const response = await getFavourites();
      if (response.data.success) {
        setFavourites(response.data.favouriteHomes);
      }
    } catch (error) {
      console.error('Error fetching favourites:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleRemoveFavourite = async (homeId) => {
    try {
      await removeFromFavourite(homeId);
      setFavourites(prev => prev.filter(home => home._id !== homeId));
    } catch (error) {
      console.error('Error removing from favourites:', error);
    }
  };

  return (
    <>
      <Navbar currentPage="favourites" />
      <main className="container mx-auto bg-white shadow-lg rounded-lg p-8 mt-10 max-w-6xl">
        <h2 className="text-3xl text-red-500 font-bold text-center mb-6">
          Here are your favourites:
        </h2>
        {loading ? (
          <div className="text-center">Loading...</div>
        ) : favourites.length === 0 ? (
          <div className="text-center text-gray-600">No favourites yet</div>
        ) : (
          <div className="flex flex-wrap justify-center gap-6">
            {favourites.map(home => (
              <HomeCard 
                key={home._id} 
                home={home}
                showRemoveFavourite={true}
                onRemoveFavourite={handleRemoveFavourite}
              />
            ))}
          </div>
        )}
      </main>
    </>
  );
};

export default FavouriteList;
