import { useState, useEffect } from 'react';
import { getHostHomes, deleteHome } from '../../services/api';
import Navbar from '../../components/Navbar';
import HomeCard from '../../components/HomeCard';

const HostHomeList = () => {
  const [homes, setHomes] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchHomes();
  }, []);

  const fetchHomes = async () => {
    try {
      const response = await getHostHomes();
      if (response.data.success) {
        setHomes(response.data.registeredHomes);
      }
    } catch (error) {
      console.error('Error fetching homes:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (homeId) => {
    if (confirm('Are you sure you want to delete this home?')) {
      try {
        await deleteHome(homeId);
        setHomes(prev => prev.filter(home => home._id !== homeId));
      } catch (error) {
        console.error('Error deleting home:', error);
      }
    }
  };

  return (
    <>
      <Navbar currentPage="host-homes" />
      <main className="container mx-auto bg-white shadow-lg rounded-lg p-8 mt-10 max-w-6xl">
        <h2 className="text-3xl text-red-500 font-bold text-center mb-6">
          Hey Host! Here are your homes:
        </h2>
        {loading ? (
          <div className="text-center">Loading...</div>
        ) : homes.length === 0 ? (
          <div className="text-center text-gray-600">No homes registered yet</div>
        ) : (
          <div className="flex flex-wrap justify-center gap-6">
            {homes.map(home => (
              <HomeCard 
                key={home._id} 
                home={home}
                showEdit={true}
                showDelete={true}
                onDelete={handleDelete}
              />
            ))}
          </div>
        )}
      </main>
    </>
  );
};

export default HostHomeList;
