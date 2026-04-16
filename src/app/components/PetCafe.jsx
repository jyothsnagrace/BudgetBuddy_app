import { useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { Coffee, MessageCircle, Sparkles } from "lucide-react";
import { API_URL } from "../../config";
import { checkCompanionAvailability } from "./FriendshipStatus";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Button } from "./ui/button";
import { ScrollArea } from "./ui/scroll-area";

import cafeBackground from "../../assets/cafe-background.jpg";
import penguinHappy from "../../assets/penguin-happy.png";
import dragonHappy from "../../assets/dragon-happy.png";
import capybaraHappy from "../../assets/capybara-happy.png";
import catHappy from "../../assets/cat-happy.png";

const companions = [
  { role: "npc_pet_1", petType: "penguin", name: "Penny", image: penguinHappy },
  { role: "barista_planner", petType: "dragon", name: "Esper", image: dragonHappy },
  { role: "npc_pet_2", petType: "capybara", name: "Capy", image: capybaraHappy },
  { role: "user_pet", petType: "cat", name: "Mochi", image: catHappy },
];

const roleMeta = {
  user_pet: { name: "Mochi 🐱", classes: "bg-pink-100 border-pink-300" },
  npc_pet_1: { name: "Penny 🐧", classes: "bg-cyan-100 border-cyan-300" },
  npc_pet_2: { name: "Capy 🦫", classes: "bg-lime-100 border-lime-300" },
  barista_planner: { name: "Esper 🐉", classes: "bg-violet-100 border-violet-300" },
};

export function PetCafe() {
  const [messages, setMessages] = useState([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [availableCompanions, setAvailableCompanions] = useState([]);
  const [hasStarted, setHasStarted] = useState(false);
  const [error, setError] = useState("");
  const [userId, setUserId] = useState(() => localStorage.getItem("userId") || "demo_user_001");
  const endRef = useRef(null);

  useEffect(() => {
    const checkAvailability = () => {
      const available = companions
        .map((companion) => ({
          ...companion,
          available: checkCompanionAvailability(companion.petType),
        }))
        .filter((companion) => companion.available);

      setAvailableCompanions(available);
    };

    checkAvailability();
    const intervalId = setInterval(checkAvailability, 60000);

    return () => clearInterval(intervalId);
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isGenerating]);

  const sortedMessages = useMemo(() => {
    return [...messages].sort((a, b) => {
      const aTime = new Date(a.timestamp || 0).getTime();
      const bTime = new Date(b.timestamp || 0).getTime();
      return aTime - bTime;
    });
  }, [messages]);

  const generateNewMessage = async () => {
    if (isGenerating || availableCompanions.length === 0) {
      return;
    }

    setIsGenerating(true);
    setError("");

    try {
      const response = await fetch(`${API_URL}/api/cafe/gossip`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ user_id: userId }),
      });

      if (!response.ok) {
        throw new Error(`Cafe request failed (${response.status})`);
      }

      const payload = await response.json();
      const incoming = payload.conversation || [];

      // Keep message ids stable enough for animation when backend omits ids.
      const normalizedIncoming = incoming.map((message, index) => ({
        ...message,
        id: message.id || `${Date.now()}-${index}`,
      }));

      setMessages((prev) => [...prev, ...normalizedIncoming]);
    } catch (err) {
      setError(err.message || "Failed to load cafe gossip.");
    } finally {
      setIsGenerating(false);
    }
  };

  const startConversation = () => {
    if (hasStarted) {
      return;
    }
    setHasStarted(true);
    generateNewMessage();
  };

  return (
    <Card className="bg-white/90 backdrop-blur-md border-2 border-amber-300 shadow-xl overflow-hidden">
      <CardHeader className="text-center bg-gradient-to-r from-amber-50 to-orange-50 border-b-2 border-amber-200">
        <CardTitle className="flex items-center justify-center gap-2">
          <Coffee className="h-6 w-6 text-amber-600" />
          <span className="bg-gradient-to-r from-amber-600 to-orange-600 bg-clip-text text-transparent">
            Pet Community Cafe
          </span>
          <Sparkles className="h-5 w-5 text-amber-500" />
        </CardTitle>
        <p className="text-sm text-gray-600 mt-1">
          Gossip, quests, and caffeinated budget drama.
        </p>
      </CardHeader>

      <CardContent className="p-0">
        <div
          className="relative h-48 sm:h-64 bg-cover bg-center border-b-2 border-amber-200"
          style={{ backgroundImage: `url(${cafeBackground})` }}
        >
          <div className="absolute inset-0 bg-gradient-to-t from-black/25 via-transparent to-black/10" />
          <div className="absolute inset-0 flex items-end justify-around pb-7 px-4">
            <AnimatePresence>
              {availableCompanions.map((companion, index) => (
                <motion.div
                  key={companion.role}
                  initial={{ y: 80, opacity: 0, scale: 0.7 }}
                  animate={{ y: 0, opacity: 1, scale: 1 }}
                  exit={{ y: 80, opacity: 0, scale: 0.7 }}
                  transition={{ delay: index * 0.12, type: "spring", stiffness: 180, damping: 14 }}
                  whileHover={{ y: -8, scale: 1.07 }}
                  className="cursor-pointer"
                >
                  <motion.img
                    src={companion.image}
                    alt={companion.name}
                    className="w-16 h-16 sm:w-20 sm:h-20 object-contain drop-shadow-xl"
                    animate={{ y: [0, -6, 0] }}
                    transition={{ duration: 2.1, repeat: Infinity, delay: index * 0.2, ease: "easeInOut" }}
                  />
                </motion.div>
              ))}
            </AnimatePresence>
          </div>

          <div className="absolute top-3 right-3 bg-white/90 rounded-full px-3 py-1 shadow-lg border border-amber-300">
            <span className="text-xs sm:text-sm font-medium text-amber-700">
              {availableCompanions.length} {availableCompanions.length === 1 ? "pet" : "pets"} in cafe
            </span>
          </div>
        </div>

        <div className="p-4">
          {!hasStarted ? (
            <div className="text-center py-7">
              <Coffee className="h-11 w-11 text-amber-400 mx-auto mb-3" />
              <p className="text-gray-600 mb-4 text-sm sm:text-base">
                {availableCompanions.length > 0
                  ? "Your companions are ready to spill budget tea."
                  : "No companions are available yet. Keep checking in to maintain friendships."}
              </p>
              <div className="flex flex-col sm:flex-row gap-2 max-w-xl mx-auto">
                <input
                  value={userId}
                  onChange={(event) => setUserId(event.target.value)}
                  placeholder="Enter user id"
                  className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm"
                />
                <Button
                  onClick={startConversation}
                  disabled={availableCompanions.length === 0 || isGenerating || !userId.trim()}
                  className="bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600"
                >
                  <MessageCircle className="h-4 w-4 mr-2" />
                  Visit Cafe
                </Button>
              </div>
            </div>
          ) : (
            <>
              <ScrollArea className="h-64 pr-4">
                <div className="space-y-3">
                  {sortedMessages.map((message) => {
                    const role = message.speaker;
                    const roleDetails = roleMeta[role] || { name: role, classes: "bg-gray-100 border-gray-300" };
                    const isQuest = role === "barista_planner" && (/quest/i.test(message.content || "") || Boolean(message.meta?.quest));

                    return (
                      <motion.div
                        key={message.id}
                        initial={{ opacity: 0, x: -18 }}
                        animate={{ opacity: 1, x: 0 }}
                        className={`p-3 rounded-lg border-2 ${roleDetails.classes} ${isQuest ? "ring-2 ring-violet-400" : ""}`}
                      >
                        <div className="flex items-start gap-2">
                          <div className="font-semibold text-sm text-gray-900 min-w-fit">
                            {roleDetails.name}{isQuest ? " • Budget Quest" : ""}
                          </div>
                          <div className="flex-1 text-sm text-gray-700 whitespace-pre-wrap">
                            {message.content}
                          </div>
                        </div>
                      </motion.div>
                    );
                  })}

                  {isGenerating && (
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="flex items-center gap-2 text-sm text-gray-500"
                    >
                      <div className="flex gap-1">
                        <motion.div
                          className="w-2 h-2 bg-amber-400 rounded-full"
                          animate={{ scale: [1, 1.45, 1] }}
                          transition={{ duration: 0.6, repeat: Infinity, delay: 0 }}
                        />
                        <motion.div
                          className="w-2 h-2 bg-amber-400 rounded-full"
                          animate={{ scale: [1, 1.45, 1] }}
                          transition={{ duration: 0.6, repeat: Infinity, delay: 0.2 }}
                        />
                        <motion.div
                          className="w-2 h-2 bg-amber-400 rounded-full"
                          animate={{ scale: [1, 1.45, 1] }}
                          transition={{ duration: 0.6, repeat: Infinity, delay: 0.4 }}
                        />
                      </div>
                      Brewing next gossip...
                    </motion.div>
                  )}
                  <div ref={endRef} />
                </div>
              </ScrollArea>

              {error && <p className="mt-3 text-sm text-red-600">{error}</p>}

              <div className="mt-4 flex gap-2">
                <Button
                  onClick={generateNewMessage}
                  disabled={isGenerating || availableCompanions.length === 0 || !userId.trim()}
                  className="w-full bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600"
                >
                  {isGenerating ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent mr-2" />
                      Chatting...
                    </>
                  ) : (
                    <>
                      <Sparkles className="h-4 w-4 mr-2" />
                      Continue Chat
                    </>
                  )}
                </Button>
              </div>
            </>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

export default PetCafe;
