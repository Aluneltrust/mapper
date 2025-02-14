import React, { useState, useEffect } from 'react';

const RouteCalculator = () => {
  const [addresses, setAddresses] = useState(['']);
  const [stateDistances, setStateDistances] = useState({});
  const [map, setMap] = useState(null);
  const [directionsService, setDirectionsService] = useState(null);
  const [directionsRenderer, setDirectionsRenderer] = useState(null);
  const [totalDistance, setTotalDistance] = useState(0);
  const [logs, setLogs] = useState([]);

  useEffect(() => {
    const script = document.createElement('script');
    script.src = `https://maps.googleapis.com/maps/api/js?key=${import.meta.env.VITE_GOOGLE_MAPS_API_KEY}&libraries=places`;
    script.async = true;
    script.onload = initializeMap;
    document.head.appendChild(script);

    return () => {
      document.head.removeChild(script);
    };
  }, []);

  const initializeMap = () => {
    const newMap = new window.google.maps.Map(document.getElementById('map'), {
      center: { lat: 39.8283, lng: -98.5795 },
      zoom: 4,
    });

    // Initialize DirectionsService and DirectionsRenderer
    const newDirectionsService = new window.google.maps.DirectionsService();
    const newDirectionsRenderer = new window.google.maps.DirectionsRenderer({
      map: newMap
    });

    setMap(newMap);
    setDirectionsService(newDirectionsService);
    setDirectionsRenderer(newDirectionsRenderer);
  };

  const handleAddressChange = (index, value) => {
    const newAddresses = [...addresses];
    newAddresses[index] = value;
    setAddresses(newAddresses);
  };

  const addAddressInput = () => {
    setAddresses([...addresses, '']);
  };

  const removeAddressInput = (index) => {
    if (addresses.length > 1) {
      const newAddresses = addresses.filter((_, i) => i !== index);
      setAddresses(newAddresses);
    }
  };

  const calculateRoute = async () => {
    if (addresses.length < 2) {
      alert('Please enter at least two addresses');
      return;
    }
  
    // Filter out empty addresses
    const validAddresses = addresses.filter(addr => addr.trim() !== '');
    
    if (validAddresses.length < 2) {
      alert('Please enter at least two valid addresses');
      return;
    }
  
    const waypoints = validAddresses.slice(1, -1).map(address => ({
      location: address,
      stopover: true
    }));
  
    const request = {
      origin: validAddresses[0],
      destination: validAddresses[validAddresses.length - 1],
      waypoints: waypoints,
      travelMode: google.maps.TravelMode.DRIVING,
      optimizeWaypoints: false,
      provideRouteAlternatives: false,
      avoidHighways: false,
      avoidTolls: false
    };
  
    try {
      directionsService.route(request, (result, status) => {
        if (status === 'OK') {
          console.log('Route calculated:', result);
          directionsRenderer.setDirections(result);
          processStateDistances(result.routes[0].legs);
        } else {
          console.error('Directions request failed due to ' + status);
          alert('Error calculating route: ' + status);
        }
      });
    } catch (error) {
      console.error('Error in calculate route:', error);
      alert('Error calculating route');
    }
  };



  const processStateDistances = async (routeLegs) => {
    try {
      // Simplify the points collection
      const allPoints = [];
      
      routeLegs.forEach(leg => {
        leg.steps.forEach(step => {
          const decodedPath = google.maps.geometry.encoding.decodePath(step.polyline.points);
          decodedPath.forEach(point => {
            allPoints.push({
              lat: point.lat(),
              lng: point.lng()
            });
          });
        });
      });
  
      // Calculate total distance
      const totalGoogleDistance = routeLegs.reduce((acc, leg) => 
        acc + leg.distance.value / 1609.34, 0);
  
      console.log('Sending to backend:', {
        points: allPoints.length,
        total_distance: totalGoogleDistance
      });
  
      const response = await fetch('http://localhost:5000/api/calculate-route', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          stops: addresses,
          route_details: allPoints,
          total_google_distance: totalGoogleDistance
        })
      });
  
      if (!response.ok) {
        const errorData = await response.text();
        throw new Error(`HTTP error! status: ${response.status}, message: ${errorData}`);
      }
  
      const data = await response.json();
      console.log('Backend response:', data);
  
      setStateDistances(data.state_distances);
      setTotalDistance(data.total_distance);
  
      const timestamp = new Date().toLocaleString();
      const logEntry = {
        timestamp,
        addresses: [...addresses],
        distances: data.state_distances,
        total: data.total_distance
      };
      setLogs(prevLogs => [logEntry, ...prevLogs]);
  
    } catch (error) {
      console.error('Error processing state distances:', error);
      console.error('Detailed error:', error.stack);
      alert('Error calculating state distances. Check console for details.');
    }

  };




  // Rest of your component's JSX remains the same
  return (
    <div className="calculator-card">
      <div className="card-header">
        <h2 className="card-title">Route Miles Calculator</h2>
        <p className="card-subtitle">Calculate interstate mileage</p>
      </div>
      
      <div className="card-content">
        {/* Address Inputs */}
        <div className="addresses-container">
          {addresses.map((address, index) => (
            <div key={index} className="input-container">
              <input
                type="text"
                value={address}
                onChange={(e) => handleAddressChange(index, e.target.value)}
                className="location-input"
                placeholder={`Address ${index + 1}`}
              />
              {addresses.length > 1 && (
                <button 
                  className="remove-button"
                  onClick={() => removeAddressInput(index)}
                >
                  Remove
                </button>
              )}
            </div>
          ))}
          
          <button 
            className="add-button"
            onClick={addAddressInput}
          >
            Add Another Address
          </button>

          <button 
            className="calculate-button"
            onClick={calculateRoute}
          >
            Calculate Miles
          </button>
        </div>

        {/* Map */}
        <div id="map" className="map-container"></div>

        {/* Current Results */}
        {Object.keys(stateDistances).length > 0 && (
          <div className="results-section">
            <h3 className="results-title">Current Route Breakdown</h3>
            <div className="state-grid">
              {Object.entries(stateDistances).map(([state, distance]) => (
                <div key={state} className="state-card">
                  <div className="state-name">{state}</div>
                  <div className="state-distance">
                    {distance.toFixed(1)}
                    <span className="distance-unit"> miles</span>
                  </div>
                </div>
              ))}
            </div>
            <div className="total-distance">
              <div className="total-label">Total Distance</div>
              <div className="total-value">{totalDistance.toFixed(1)} miles</div>
            </div>
          </div>
        )}

        {/* Logs Section */}
        {logs.length > 0 && (
          <div className="logs-section">
            <h3 className="logs-title">Route History</h3>
            {logs.map((log, index) => (
              <div key={index} className="log-entry">
                {/* <div className="log-timestamp">{log.timestamp}</div> */}
                {/* <div className="log-addresses">
                  {log.addresses.map((addr, i) => (
                    <div key={i} className="log-address">Stop {i + 1}: {addr}</div>
                  ))}
                </div> */}
                <div className="log-distances">
                  {Object.entries(log.distances).map(([state, distance]) => (
                    <div key={state} className="log-distance">
                      {state}: {distance.toFixed(1)} miles
                    </div>
                  ))}
                  <div className="log-total">
                    Total: {log.total.toFixed(1)} miles
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );

};

export default RouteCalculator;