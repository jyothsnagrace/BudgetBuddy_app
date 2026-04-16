import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Button } from "./ui/button";
import { checkCompanionAvailability } from "./FriendshipStatus";
import { Lock, Sparkles } from "lucide-react";
import { API_URL } from "../../config";

export function CompanionSelector() {
  const [selectedPet, setSelectedPet] = useState<'penguin' | 'dragon' | 'capybara' | 'cat'>(() => {
    const saved = localStorage.getItem('selectedPet');
    return (saved as 'penguin' | 'dragon' | 'capybara' | 'cat') || 'penguin';
  });

  const [availablePets, setAvailablePets] = useState({
    penguin: true,
    dragon: true,
    capybara: true,
    cat: true
  });

  useEffect(() => {
    const checkAvailability = () => {
      setAvailablePets({
        penguin: checkCompanionAvailability('penguin'),
        dragon: checkCompanionAvailability('dragon'),
        capybara: checkCompanionAvailability('capybara'),
        cat: checkCompanionAvailability('cat')
      });
    };

    checkAvailability();
    const interval = setInterval(checkAvailability, 60000); // Check every minute

    return () => clearInterval(interval);
  }, []);

  const handlePetChange = async (pet: 'penguin' | 'dragon' | 'capybara' | 'cat') => {
    if (!availablePets[pet]) return; // Don't allow selecting locked pets
    
    setSelectedPet(pet);
    localStorage.setItem('selectedPet', pet);
    
    // Save to backend
    const token = localStorage.getItem("token");
    if (token) {
      try {
        await fetch(`${API_URL}/api/user/profile`, {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`,
          },
          body: JSON.stringify({ selected_pet: pet }),
        });
      } catch (error) {
        console.error("Failed to save pet selection:", error);
      }
    }
    
    // Trigger a storage event for same-tab updates
    window.dispatchEvent(new Event('storage'));
  };

  useEffect(() => {
    const handleStorageChange = () => {
      const saved = localStorage.getItem('selectedPet');
      setSelectedPet((saved as 'penguin' | 'dragon' | 'capybara' | 'cat') || 'penguin');
    };
    
    window.addEventListener('storage', handleStorageChange);
    return () => window.removeEventListener('storage', handleStorageChange);
  }, []);

  return (
    <Card className="bg-white/85 backdrop-blur-md border-2 border-purple-300 shadow-lg">
      <CardHeader className="text-center">
        <CardTitle className="flex items-center justify-center gap-2 text-lg">
          <Sparkles className="h-5 w-5 text-purple-600" />
          Choose Your Companion
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex flex-wrap justify-center gap-3">
          <Button
            onClick={() => handlePetChange('penguin')}
            variant={selectedPet === 'penguin' ? 'default' : 'outline'}
            disabled={!availablePets.penguin}
            className={`text-base px-6 py-5 ${
              selectedPet === 'penguin' 
                ? 'bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-600 hover:to-blue-600' 
                : !availablePets.penguin 
                ? 'opacity-50 cursor-not-allowed' 
                : ''
            }`}
            size="lg"
          >
            {availablePets.penguin ? '🐧 Penny' : <><Lock className="h-4 w-4 mr-1" /> 🐧 Penny</>}
          </Button>
          <Button
            onClick={() => handlePetChange('dragon')}
            variant={selectedPet === 'dragon' ? 'default' : 'outline'}
            disabled={!availablePets.dragon}
            className={`text-base px-6 py-5 ${
              selectedPet === 'dragon' 
                ? 'bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600' 
                : !availablePets.dragon 
                ? 'opacity-50 cursor-not-allowed' 
                : ''
            }`}
            size="lg"
          >
            {availablePets.dragon ? '🐉 Esper' : <><Lock className="h-4 w-4 mr-1" /> 🐉 Esper</>}
          </Button>
          <Button
            onClick={() => handlePetChange('capybara')}
            variant={selectedPet === 'capybara' ? 'default' : 'outline'}
            disabled={!availablePets.capybara}
            className={`text-base px-6 py-5 ${
              selectedPet === 'capybara' 
                ? 'bg-gradient-to-r from-green-500 to-lime-500 hover:from-green-600 hover:to-lime-600' 
                : !availablePets.capybara 
                ? 'opacity-50 cursor-not-allowed' 
                : ''
            }`}
            size="lg"
          >
            {availablePets.capybara ? '🦫 Capy' : <><Lock className="h-4 w-4 mr-1" /> 🦫 Capy</>}
          </Button>
          <Button
            onClick={() => handlePetChange('cat')}
            variant={selectedPet === 'cat' ? 'default' : 'outline'}
            disabled={!availablePets.cat}
            className={`text-base px-6 py-5 ${
              selectedPet === 'cat' 
                ? 'bg-gradient-to-r from-pink-400 to-rose-500 hover:from-pink-500 hover:to-rose-600' 
                : !availablePets.cat 
                ? 'opacity-50 cursor-not-allowed' 
                : ''
            }`}
            size="lg"
          >
            {availablePets.cat ? '🐱 Mochi' : <><Lock className="h-4 w-4 mr-1" /> 🐱 Mochi</>}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}