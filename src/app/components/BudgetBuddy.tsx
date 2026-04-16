import { useState, useEffect, useRef } from "react";
import { motion } from "motion/react";
import { Send, Sparkles, Heart, MapPin } from "lucide-react";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { ScrollArea } from "./ui/scroll-area";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from "./ui/select";
import { FriendshipStatus, updateLastActivity } from "./FriendshipStatus";
import { API_URL } from "../../config";

import penguinHappy from "../../assets/penguin-happy.png";
import penguinWorried from "../../assets/penguin-worried.png";
import penguinExcited from "../../assets/penguin-excited.png";
import dragonHappy from "../../assets/dragon-happy.png";
import dragonSad from "../../assets/dragon-sad.png";
import capybaraHappy from "../../assets/capybara-happy.png";
import capybaraStressed from "../../assets/capybara-stressed.png";
import capybaraCalm from "../../assets/capybara-sad.png";
import catHappy from "../../assets/cat-happy.png";
import catSad from "../../assets/cat-sad.png";

interface Message {
  id: string;
  text: string;
  sender: "user" | "buddy";
  timestamp: Date;
}

interface BudgetBuddyProps {
  totalSpent: number;
  budget: number;
  recentExpenses: Array<{
    amount: number;
    category: string;
    description: string;
  }>;
  categoryTotals: { [key: string]: number };
}

type CityRegion = "Northeast" | "Midwest" | "South" | "West";

type CityOption = {
  value: string;
  label: string;
  state: string;
  region: CityRegion;
};

const CITY_OPTIONS: CityOption[] = [
  { value: "Austin", label: "Austin, TX", state: "TX", region: "South" },
  { value: "Atlanta", label: "Atlanta, GA", state: "GA", region: "South" },
  { value: "Boston", label: "Boston, MA", state: "MA", region: "Northeast" },
  { value: "Charlotte", label: "Charlotte, NC", state: "NC", region: "South" },
  { value: "Chicago", label: "Chicago, IL", state: "IL", region: "Midwest" },
  { value: "Columbus", label: "Columbus, OH", state: "OH", region: "Midwest" },
  { value: "Dallas", label: "Dallas, TX", state: "TX", region: "South" },
  { value: "Denver", label: "Denver, CO", state: "CO", region: "West" },
  { value: "Detroit", label: "Detroit, MI", state: "MI", region: "Midwest" },
  { value: "Fort Worth", label: "Fort Worth, TX", state: "TX", region: "South" },
  { value: "Houston", label: "Houston, TX", state: "TX", region: "South" },
  { value: "Indianapolis", label: "Indianapolis, IN", state: "IN", region: "Midwest" },
  { value: "Jacksonville", label: "Jacksonville, FL", state: "FL", region: "South" },
  { value: "Las Vegas", label: "Las Vegas, NV", state: "NV", region: "West" },
  { value: "Los Angeles", label: "Los Angeles, CA", state: "CA", region: "West" },
  { value: "Miami", label: "Miami, FL", state: "FL", region: "South" },
  { value: "Nashville", label: "Nashville, TN", state: "TN", region: "South" },
  { value: "New York", label: "New York, NY", state: "NY", region: "Northeast" },
  { value: "Philadelphia", label: "Philadelphia, PA", state: "PA", region: "Northeast" },
  { value: "Phoenix", label: "Phoenix, AZ", state: "AZ", region: "West" },
  { value: "Portland", label: "Portland, OR", state: "OR", region: "West" },
  { value: "San Antonio", label: "San Antonio, TX", state: "TX", region: "South" },
  { value: "San Diego", label: "San Diego, CA", state: "CA", region: "West" },
  { value: "San Francisco", label: "San Francisco, CA", state: "CA", region: "West" },
  { value: "San Jose", label: "San Jose, CA", state: "CA", region: "West" },
  { value: "Seattle", label: "Seattle, WA", state: "WA", region: "West" },
  { value: "Washington", label: "Washington, DC", state: "DC", region: "Northeast" },
];

const REGION_ORDER: CityRegion[] = ["Northeast", "Midwest", "South", "West"];

/* ================= ENHANCED BACKEND CHAT ================= */

async function chatWithBackend(message: string, city?: string) {
  const token = localStorage.getItem("token");
  
  if (!token) {
    return "Please login to chat with me! 🔒";
  }

  try {
    const response = await fetch(`${API_URL}/api/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`,
      },
      body: JSON.stringify({
        message: message,
        city: city || null,
        context: {}
      }),
    });

    if (!response.ok) {
      throw new Error("Chat request failed");
    }

    const data = await response.json();
    return data.response || "Sorry, I couldn't generate a response 😅";
  } catch (error) {
    console.error("Chat error:", error);
    return "Oops, I'm having connection trouble! Try again? 💭";
  }
}

/* ================= COMPONENT ================= */

export function BudgetBuddy({
  totalSpent,
  budget,
  recentExpenses,
  categoryTotals,
}: BudgetBuddyProps) {
  const [petType, setPetType] = useState<'penguin' | 'dragon' | 'capybara' | 'cat'>(() => {
    const saved = localStorage.getItem('selectedPet');
    return (saved as 'penguin' | 'dragon' | 'capybara' | 'cat') || 'penguin';
  });
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [city, setCity] = useState(() => localStorage.getItem("selectedCity") || "");
  const [cityFilter, setCityFilter] = useState("");
  const [isCityOpen, setIsCityOpen] = useState(false);
  const [buddyMood, setBuddyMood] = useState<"happy" | "worried" | "excited">(
    "happy"
  );
  const scrollRef = useRef<HTMLDivElement>(null);
  const chatCardRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const [petAnimation, setPetAnimation] = useState(0);

  /* ===== Save Pet Selection ===== */
  
  useEffect(() => {
    localStorage.setItem('selectedPet', petType);
  }, [petType]);

  useEffect(() => {
    localStorage.setItem("selectedCity", city);
  }, [city]);

  /* ===== Listen for Pet Changes ===== */
  
  useEffect(() => {
    const handleStorageChange = () => {
      const saved = localStorage.getItem('selectedPet');
      if (saved && saved !== petType) {
        setPetType(saved as 'penguin' | 'dragon' | 'capybara' | 'cat');
      }
    };
    
    window.addEventListener('storage', handleStorageChange);
    
    // Also check periodically for same-tab changes
    const interval = setInterval(() => {
      const saved = localStorage.getItem('selectedPet');
      const currentPet = (saved as 'penguin' | 'dragon' | 'capybara' | 'cat') || 'penguin';
      if (currentPet !== petType) {
        setPetType(currentPet);
      }
    }, 100);
    
    return () => {
      window.removeEventListener('storage', handleStorageChange);
      clearInterval(interval);
    };
  }, [petType]);

  /* ===== Mood ===== */

  useEffect(() => {
    const percent = budget > 0 ? (totalSpent / budget) * 100 : 0;
    if (percent < 60) setBuddyMood("happy");
    else if (percent < 90) setBuddyMood("worried");
    else setBuddyMood("excited");
  }, [totalSpent, budget]);

  /* ===== Initial Greeting ===== */

  useEffect(() => {
    const petName = getPetName();
    const cityText = city ? ` I see you're in ${city}! 📍` : '';
    
    const greetingText = petType === 'penguin'
      ? `Hi! I'm Penny 🐧 — your budgeting buddy.${cityText} Ask me anything about your spending or local costs!`
      : petType === 'dragon'
      ? `Greetings! I'm Esper 🐉 — guardian of your treasure hoard.${cityText} Ask me for ancient wisdom about spending!`
      : petType === 'cat'
      ? `*Purrs* Hello! I'm Mochi 🐱 — your sassy money friend.${cityText} Ask me anything, fur real!`
      : `Hey there! I'm Capy 🦫 — your chill budgeting buddy.${cityText} No stress, just ask me anything!`
    
    setMessages([
      {
        id: "1",
        text: greetingText,
        sender: "buddy",
        timestamp: new Date(),
      },
    ]);
  }, [petType, city]);

  /* ===== Auto Scroll (only on new messages, not on pet change) ===== */

  const prevMessageLengthRef = useRef(messages.length);
  
  useEffect(() => {
    // Only scroll if a new message was added (not when messages were reset)
    if (messages.length > prevMessageLengthRef.current) {
      // First, ensure chat card is visible (minimal scroll if needed)
      if (chatCardRef.current) {
        const rect = chatCardRef.current.getBoundingClientRect();
        const isVisible = rect.top >= 0 && rect.bottom <= window.innerHeight;
        
        if (!isVisible) {
          // Scroll chat card into view with minimal movement
          chatCardRef.current.scrollIntoView({ behavior: "smooth", block: "nearest" });
        }
      }
      
      // Then scroll within the chat container to show the new message
      setTimeout(() => {
        scrollRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "nearest" });
      }, 100);
    }
    prevMessageLengthRef.current = messages.length;
  }, [messages]);

  useEffect(() => {
    if (!isCityOpen) {
      setCityFilter("");
    }
  }, [isCityOpen]);

  /* ===== Send Message ===== */

  const handleSendMessage = async () => {
    if (!input.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      text: input,
      sender: "user",
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    const currentInput = input;
    setInput("");
    setPetAnimation((p) => p + 1);

    try {
      // Use enhanced backend API with city support
      const reply = await chatWithBackend(currentInput, city || undefined);

      setMessages((prev) => [
        ...prev,
        {
          id: Date.now().toString(),
          text: reply,
          sender: "buddy",
          timestamp: new Date(),
        },
      ]);
      
      // Update last activity for friendship level
      updateLastActivity();
    } catch (error) {
      const petName = getPetName();
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now().toString(),
          text: `Oops — ${petName} couldn't connect! 😢 Try again?`,
          sender: "buddy",
          timestamp: new Date(),
        },
      ]);
    } finally {
      // Focus back on input for quick follow-up questions (without scrolling page)
      setTimeout(() => inputRef.current?.focus({ preventScroll: true }), 100);
    }
  };

  /* ===== Helpers ===== */

  const getBuddyImage = () => {
    if (petType === 'penguin') {
      return buddyMood === "happy"
        ? penguinHappy
        : buddyMood === "worried"
        ? penguinWorried
        : penguinExcited;
    } else if (petType === 'dragon') {
      // Dragon: happy when budget is good, sad when bad
      const percent = budget > 0 ? (totalSpent / budget) * 100 : 0;
      return percent < 80 ? dragonHappy : dragonSad;
    } else if (petType === 'cat') {
      return buddyMood === "happy"
        ? catHappy
        : catSad;
    } else {
      // Capybara: happy when budget is good, stressed when bad
      const percent = budget > 0 ? (totalSpent / budget) * 100 : 0;
      return percent < 80 ? capybaraHappy : capybaraStressed;
    }
  };

  const getMoodDescription = () => {
    const percent = budget > 0 ? (totalSpent / budget) * 100 : 0;
    
    if (petType === 'penguin') {
      if (percent < 60) return "Feeling happy 😊";
      if (percent < 90) return "A bit worried 😟";
      return "Over budget 😱";
    } else if (petType === 'dragon') {
      // Dragon moods
      if (percent < 60) return "Guarding treasure ✨";
      if (percent < 80) return "Watching closely 👀";
      return "Treasure low! 🔥";
    } else if (petType === 'cat') {
      if (percent < 60) return "Playful and happy 😸";
      if (percent < 90) return "A bit concerned 🤔";
      return "Budget tight! 💰";
    } else {
      // Capybara moods
      if (percent < 60) return "Calm and collected 🧘‍♂️";
      if (percent < 80) return "Stressed but trying 🤔";
      return "Budget tight! 💰";
    }
  };

  const getPetName = () => petType === 'penguin' ? 'Penny' : petType === 'dragon' ? 'Esper' : petType === 'cat' ? 'Mochi' : 'Capy';
  const getPetTitle = () => petType === 'penguin' ? 'Penny the Penguin' : petType === 'dragon' ? 'Esper the Dragon' : petType === 'cat' ? 'Mochi the Cat' : 'Capy the Capybara';
  const getPetIcon = () => petType === 'penguin' ? '🐧' : petType === 'dragon' ? '🐉' : petType === 'cat' ? '🐱' : '🦫';

  const handlePetClick = () => setPetAnimation((p) => p + 1);

  const handlePetChange = (newPet: 'penguin' | 'dragon' | 'capybara' | 'cat') => {
    setPetType(newPet);
    setPetAnimation((p) => p + 1);
  };

  const normalizedCityFilter = cityFilter.trim().toLowerCase();
  const filteredCities = normalizedCityFilter
    ? CITY_OPTIONS.filter((option) =>
        `${option.value} ${option.label} ${option.state}`
          .toLowerCase()
          .includes(normalizedCityFilter),
      )
    : CITY_OPTIONS;

  const cityGroups = REGION_ORDER.map((region) => {
    const cities = filteredCities
      .filter((option) => option.region === region)
      .sort((a, b) => a.label.localeCompare(b.label));
    return { region, cities };
  }).filter((group) => group.cities.length > 0);

  /* ================= UI ================= */

  return (
    <div className="space-y-4">
      {/* Pet Card */}

      <Card className={`border-2 ${petType === 'penguin' ? 'border-cyan-300' : petType === 'dragon' ? 'border-purple-300' : petType === 'cat' ? 'border-pink-300' : 'border-green-300'} bg-white/85 shadow-lg`}>
        <CardHeader className="text-center">
          <CardTitle className="flex justify-center gap-2">
            <Heart className="h-5 w-5 text-pink-500 fill-pink-500" />
            {getPetTitle()}
            <Heart className="h-5 w-5 text-pink-500 fill-pink-500" />
          </CardTitle>
        </CardHeader>

        <CardContent>
          <motion.div
            onClick={handlePetClick}
            className="flex flex-col items-center cursor-pointer"
            whileHover={{ scale: 1.05 }}
          >
            <motion.img
              key={petAnimation}
              src={getBuddyImage()}
              className="w-40 h-40 object-contain"
              animate={{ y: [0, -10, 0] }}
              transition={{ duration: 0.6 }}
            />

            <div className={`mt-2 px-4 py-1 rounded-full border ${petType === 'penguin' ? 'border-cyan-300 bg-cyan-50' : petType === 'dragon' ? 'border-purple-300 bg-purple-50' : petType === 'cat' ? 'border-pink-300 bg-pink-50' : 'border-green-300 bg-green-50'}`}>
              <span className="text-xs text-gray-500">Mood: </span>
              {getMoodDescription()}
            </div>

            <Sparkles className={`mt-2 ${petType === 'penguin' ? 'text-cyan-400' : petType === 'dragon' ? 'text-purple-400' : petType === 'cat' ? 'text-pink-400' : 'text-green-400'}`} />
          </motion.div>

          {/* Friendship Status Bar - Based on App Activity */}
          <div className="mt-6 pt-4 border-t">
            <p className="text-xs text-gray-500 mb-2">Friendship Level</p>
            <FriendshipStatus petType={petType} />
          </div>
        </CardContent>
      </Card>

      {/* Chat */}

      <Card ref={chatCardRef} className={`border-2 ${petType === 'penguin' ? 'border-cyan-300' : petType === 'dragon' ? 'border-purple-300' : petType === 'cat' ? 'border-pink-300' : 'border-green-300'} bg-white/85 shadow-lg`}>
        <CardHeader className="space-y-1 pb-3">
          <CardTitle className="text-xl font-bold">Ask Your AI Advisor</CardTitle>
          <p className="text-sm text-gray-600">
            Get location-aware financial advice from {getPetName()}!
          </p>
        </CardHeader>

        <CardContent className="space-y-4">
          {/* City Selector */}
          <div className="flex items-center gap-2">
            <MapPin className="h-4 w-4 text-gray-500 flex-shrink-0" />
            <Select value={city} onValueChange={setCity} onOpenChange={setIsCityOpen}>
              <SelectTrigger className="flex-1">
                <SelectValue placeholder="Select a city (optional)" />
              </SelectTrigger>
              <SelectContent>
                <div className="px-2 pt-2">
                  <Input
                    value={cityFilter}
                    onChange={(event) => setCityFilter(event.target.value)}
                    onClick={(event) => event.stopPropagation()}
                    onKeyDown={(event) => event.stopPropagation()}
                    placeholder="Search cities..."
                    className="h-8"
                  />
                </div>
                {cityGroups.length === 0 ? (
                  <div className="px-2 py-2 text-xs text-muted-foreground">
                    No cities match your search.
                  </div>
                ) : (
                  cityGroups.map((group) => (
                    <SelectGroup key={group.region}>
                      <SelectLabel>{group.region}</SelectLabel>
                      {group.cities.map((option) => (
                        <SelectItem key={option.value} value={option.value}>
                          {option.label}
                        </SelectItem>
                      ))}
                    </SelectGroup>
                  ))
                )}
              </SelectContent>
            </Select>
          </div>

          {/* Example Questions */}
          <div className="bg-purple-50 border border-purple-200 rounded-lg p-1.5 space-y-1">
            <p className="text-sm font-normal text-purple-600 flex items-center gap-1 leading-tight">
              <Sparkles className="h-3 w-3 text-black" />
              Try asking:
            </p>
            <div className="space-y-0.5 pl-4">
              <button
                type="button"
                onClick={() => {
                  setInput(`Is it smarter to buy or rent in ${city || 'Charlotte'}?`);
                  setTimeout(() => inputRef.current?.focus({ preventScroll: true }), 50);
                }}
                className="flex items-start gap-2 text-[11px] text-gray-500 hover:text-purple-600 hover:bg-purple-50 w-full text-left p-1 rounded transition-colors leading-tight"
              >
                <span className="text-[10px] flex-shrink-0">🏠</span>
                <span className="text-[11px] text-gray-500 leading-tight">
                  "Is it smarter to buy or rent in {city || 'Charlotte'}?"
                </span>
              </button>
              <button
                type="button"
                onClick={() => {
                  setInput(`Which are budget friendly restaurants in ${city || 'Charlotte'}?`);
                  setTimeout(() => inputRef.current?.focus({ preventScroll: true }), 50);
                }}
                className="flex items-start gap-2 text-[11px] text-gray-500 hover:text-purple-600 hover:bg-purple-50 w-full text-left p-1 rounded transition-colors leading-tight"
              >
                <span className="text-[10px] flex-shrink-0">🍽️</span>
                <span className="text-[11px] text-gray-500 leading-tight">
                  "Which are budget friendly restaurants in {city || 'Charlotte'}?"
                </span>
              </button>
              <button
                type="button"
                onClick={() => {
                  setInput(`How does my spending compare to ${city || 'Charlotte'} average?`);
                  setTimeout(() => inputRef.current?.focus({ preventScroll: true }), 50);
                }}
                className="flex items-start gap-2 text-[11px] text-gray-500 hover:text-purple-600 hover:bg-purple-50 w-full text-left p-1 rounded transition-colors leading-tight"
              >
                <span className="text-[10px] flex-shrink-0">📊</span>
                <span className="text-[11px] text-gray-500 leading-tight">
                  "How does my spending compare to {city || 'Charlotte'} average?"
                </span>
              </button>
              <button
                type="button"
                onClick={() => {
                  setInput(`What's the cost of living in ${city || 'Charlotte'}?`);
                  setTimeout(() => inputRef.current?.focus({ preventScroll: true }), 50);
                }}
                className="flex items-start gap-2 text-[11px] text-gray-500 hover:text-purple-600 hover:bg-purple-50 w-full text-left p-1 rounded transition-colors leading-tight"
              >
                <span className="text-[10px] flex-shrink-0">🏠</span>
                <span className="text-[11px] text-gray-500 leading-tight">
                  "What's the cost of living in {city || 'Charlotte'}?"
                </span>
              </button>
            </div>
          </div>

          {/* Chat Messages */}
          <ScrollArea className="h-64 bg-gray-50 border border-gray-200 rounded-lg p-3">
            {messages.map((m) => (
              <div
                key={m.id}
                className={`mb-3 flex ${
                  m.sender === "user" ? "justify-end" : "justify-start"
                }`}
              >
                <div
                  className={`px-4 py-2.5 rounded-2xl max-w-[85%] shadow-sm ${
                    m.sender === "user"
                      ? "bg-blue-500 text-white"
                      : "bg-white border border-gray-200 text-gray-800"
                  }`}
                >
                  {m.text}
                </div>
              </div>
            ))}
            <div ref={scrollRef} />
          </ScrollArea>

          {/* Input Form */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSendMessage();
            }}
            className="flex gap-2"
          >
            <Input
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={city ? `Ask about ${city}...` : `Ask about Charlotte...`}
              className="flex-1"
            />

            <Button 
              type="submit" 
              size="icon"
              className="bg-black hover:bg-gray-800 rounded-lg"
            >
              <Send className="h-4 w-4" />
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}