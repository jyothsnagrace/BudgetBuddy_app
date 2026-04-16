import { useEffect, useState } from "react";
import { Heart, AlertTriangle, X } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Progress } from "./ui/progress";

interface FriendshipStatusProps {
  petType: 'penguin' | 'dragon' | 'capybara' | 'cat';
}

export function FriendshipStatus({ petType }: FriendshipStatusProps) {
  const [status, setStatus] = useState<{
    level: number;
    status: 'happy' | 'declining' | 'warning' | 'left';
    daysInactive: number;
    message: string;
  }>({ level: 100, status: 'happy', daysInactive: 0, message: '' });

  useEffect(() => {
    const calculateStatus = () => {
      const lastActivity = localStorage.getItem('lastActivityDate');
      const now = new Date();
      const lastDate = lastActivity ? new Date(lastActivity) : now;
      const daysSinceActivity = Math.floor((now.getTime() - lastDate.getTime()) / (1000 * 60 * 60 * 24));

      // Different thresholds for each pet
      const thresholds = {
        capybara: 30,  // 1 month
        dragon: 60,    // 2 months
        cat: 120,      // 4 months
        penguin: 240   // 8 months
      };

      const threshold = thresholds[petType];
      const level = Math.max(0, Math.min(100, 100 - (daysSinceActivity / threshold) * 100));

      let status: 'happy' | 'declining' | 'warning' | 'left' = 'happy';
      let message = '';

      if (daysSinceActivity >= threshold) {
        status = 'left';
        message = getPetName() + ' has left... 💔';
      } else if (level < 20) {
        status = 'warning';
        message = getPetName() + ' is about to leave! 😢';
      } else if (level < 50) {
        status = 'declining';
        message = getPetName() + ' misses you... 😔';
      } else {
        status = 'happy';
        message = getPetName() + ' is your friend! 💙';
      }

      setStatus({ level, status, daysInactive: daysSinceActivity, message });
    };

    calculateStatus();
    const interval = setInterval(calculateStatus, 60000); // Update every minute

    return () => clearInterval(interval);
  }, [petType]);

  const getPetName = () => {
    switch (petType) {
      case 'penguin': return 'Penny';
      case 'dragon': return 'Esper';
      case 'cat': return 'Mochi';
      case 'capybara': return 'Capy';
    }
  };

  const getStatusColor = () => {
    switch (status.status) {
      case 'happy': return 'bg-blue-500';
      case 'declining': return 'bg-yellow-500';
      case 'warning': return 'bg-orange-500';
      case 'left': return 'bg-gray-400';
    }
  };

  const getStatusIcon = () => {
    switch (status.status) {
      case 'happy': return <Heart className="h-4 w-4 text-blue-500 fill-blue-500" />;
      case 'declining': return <Heart className="h-4 w-4 text-yellow-500" />;
      case 'warning': return <AlertTriangle className="h-4 w-4 text-orange-500" />;
      case 'left': return <X className="h-4 w-4 text-gray-500" />;
    }
  };

  const getThresholdDays = () => {
    switch (petType) {
      case 'capybara': return 30;
      case 'dragon': return 60;
      case 'cat': return 120;
      case 'penguin': return 240;
    }
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {getStatusIcon()}
          <span className="text-sm font-medium">{status.message}</span>
        </div>
        <span className="text-xs text-gray-500">
          {status.daysInactive} / {getThresholdDays()} days
        </span>
      </div>
      <Progress value={status.level} className="h-2" indicatorClassName={getStatusColor()} />
      {status.status === 'warning' && (
        <p className="text-xs text-orange-600 mt-1">
          ⚠️ Come back soon or {getPetName()} will leave!
        </p>
      )}
      {status.status === 'left' && (
        <p className="text-xs text-gray-600 mt-1">
          💔 {getPetName()} left due to inactivity. Keep visiting to maintain friendships!
        </p>
      )}
    </div>
  );
}

export function checkCompanionAvailability(petType: 'penguin' | 'dragon' | 'capybara' | 'cat'): boolean {
  const lastActivity = localStorage.getItem('lastActivityDate');
  if (!lastActivity) return true;

  const now = new Date();
  const lastDate = new Date(lastActivity);
  const daysSinceActivity = Math.floor((now.getTime() - lastDate.getTime()) / (1000 * 60 * 60 * 24));

  const thresholds = {
    capybara: 30,  // 1 month
    dragon: 60,    // 2 months
    cat: 120,      // 4 months
    penguin: 240   // 8 months
  };

  return daysSinceActivity < thresholds[petType];
}

export function updateLastActivity() {
  localStorage.setItem('lastActivityDate', new Date().toISOString());
}