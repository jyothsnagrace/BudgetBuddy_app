import { useState, useEffect } from "react";
import { Sparkles, LogOut } from "lucide-react";
import { BudgetSummary } from "./components/BudgetSummary";
import { SpendingForm } from "./components/SpendingForm";
import { ExpenseList } from "./components/ExpenseList";
import { BudgetBuddy } from "./components/BudgetBuddy";
import { BudgetSettings } from "./components/BudgetSettings";
import { SpendingGraph } from "./components/SpendingGraph";
import { SpendingCalendar } from "./components/SpendingCalendar";
import { CompanionSelector } from "./components/CompanionSelector";
import { PetCafe } from "./components/PetCafe";
import { Login } from "./components/Login";
import { updateLastActivity } from "./components/FriendshipStatus";
import { Button } from "./components/ui/button";
import { API_URL } from "../config";
import snowyBackground from "../assets/background-snowy.png";
import dragonBackground from "../assets/background-dragon.png";
import capybaraBackground from "../assets/background-capybara.png";
import catBackground from "../assets/background-cat.png";

interface Expense {
  id: string;
  amount: number;
  category: string;
  description: string;
  date: string;
  created_at: string;
}

// Category mapping helpers
const frontendToBackendCategory = (frontendCat: string): string => {
  const categoryMap: { [key: string]: string } = {
    "🍕 Food": "Food",
    "🏠 Housing": "Bills",
    "🚗 Transportation": "Transportation",
    "🎮 Entertainment": "Entertainment",
    "🛍️ Shopping": "Shopping",
    "💊 Healthcare": "Healthcare",
    "📚 Education": "Education",
    "💰 Other": "Other",
  };
  return categoryMap[frontendCat] || "Other";
};

const backendToFrontendCategory = (backendCat: string): string => {
  const categoryMap: { [key: string]: string } = {
    "Food": "🍕 Food",
    "Bills": "🏠 Housing",
    "Transportation": "🚗 Transportation",
    "Entertainment": "🎮 Entertainment",
    "Shopping": "🛍️ Shopping",
    "Healthcare": "💊 Healthcare",
    "Education": "📚 Education",
    "Other": "💰 Other",
  };
  return categoryMap[backendCat] || "💰 Other";
};

export default function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  
  const [username, setUsername] = useState("");

  const [budget, setBudget] = useState(() => {
    const saved = localStorage.getItem("budget");
    return saved ? parseFloat(saved) : 2000;
  });

  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [isLoadingExpenses, setIsLoadingExpenses] = useState(false);
  const [expenseError, setExpenseError] = useState<string | null>(null);

  const [selectedPet, setSelectedPet] = useState<'penguin' | 'dragon' | 'capybara' | 'cat'>(() => {
    const saved = localStorage.getItem('selectedPet');
    return (saved as 'penguin' | 'dragon' | 'capybara' | 'cat') || 'penguin';
  });

  // Check for existing session on mount (page reload)
  useEffect(() => {
    const token = localStorage.getItem("token");
    const storedUsername = localStorage.getItem("username");
    
    if (token && storedUsername) {
      setIsAuthenticated(true);
      setUsername(storedUsername);
      
      // Keep page at top on reload (same as after login)
      setTimeout(() => {
        window.scrollTo({ top: 0, behavior: "auto" });
      }, 0);
    }
  }, []); // Run once on mount

  // Fetch expenses from backend on mount if authenticated
  useEffect(() => {
    if (isAuthenticated) {
      updateLastActivity();
      fetchExpenses();
      
      // Keep page at top when authenticated state changes
      window.scrollTo({ top: 0, behavior: "auto" });
    }
  }, [isAuthenticated]);

  const forceLogout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("username");
    localStorage.removeItem("userId");
    localStorage.removeItem("selectedPet");
    setIsAuthenticated(false);
    setUsername("");
    setSelectedPet('penguin');
    setExpenses([]);
  };

  const fetchExpenses = async () => {
    const token = localStorage.getItem("token");
    if (!token) return;

    setIsLoadingExpenses(true);
    try {
      const response = await fetch(`${API_URL}/api/expenses`, {
        headers: {
          "Authorization": `Bearer ${token}`,
        },
      });

      if (response.status === 401) {
        forceLogout();
        return;
      }

      if (response.ok) {
        const data = await response.json();
        // Map backend expense_date and category to frontend format
        const mappedExpenses = (data.expenses || []).map((expense: any) => {
          const frontendCategory = backendToFrontendCategory(expense.category);
          console.log(`Mapping category: "${expense.category}" -> "${frontendCategory}"`);
          return {
            id: expense.id,
            amount: expense.amount,
            category: frontendCategory,
            description: expense.description,
            date: expense.expense_date,
            created_at: expense.created_at,
          };
        });
        setExpenses(mappedExpenses);
      }
    } catch (error) {
      console.error("Failed to fetch expenses:", error);
    } finally {
      setIsLoadingExpenses(false);
    }
  };

  // Listen for pet changes from localStorage
  useEffect(() => {
    const handleStorageChange = () => {
      const saved = localStorage.getItem('selectedPet');
      setSelectedPet((saved as 'penguin' | 'dragon' | 'capybara' | 'cat') || 'penguin');
    };
    
    window.addEventListener('storage', handleStorageChange);
    
    // Also check periodically for same-tab changes
    const interval = setInterval(() => {
      const saved = localStorage.getItem('selectedPet');
      const currentPet = (saved as 'penguin' | 'dragon' | 'capybara' | 'cat') || 'penguin';
      if (currentPet !== selectedPet) {
        setSelectedPet(currentPet);
      }
    }, 100);
    
    return () => {
      window.removeEventListener('storage', handleStorageChange);
      clearInterval(interval);
    };
  }, [selectedPet]);

  // Save to localStorage whenever data changes
  useEffect(() => {
    localStorage.setItem("budget", budget.toString());
  }, [budget]);

  // No longer saving expenses to localStorage - using backend instead

  const handleAddExpense = async (
    expenseData: Omit<Expense, "id">,
  ) => {
    const token = localStorage.getItem("token");
    if (!token) return;

    try {
      // Convert frontend emoji category to backend category
      const backendCategory = frontendToBackendCategory(expenseData.category);
      console.log(`Adding expense: frontend category "${expenseData.category}" -> backend "${backendCategory}"`);
      
      // Already formatted as local YYYY-MM-DD by SpendingForm
      const formattedDate = expenseData.date;
      
      const response = await fetch(`${API_URL}/api/expenses`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`,
        },
        body: JSON.stringify({
          amount: expenseData.amount,
          category: backendCategory,
          description: expenseData.description,
          date: formattedDate,
        }),
      });

      if (response.status === 401) {
        forceLogout();
        return;
      }

      if (response.ok) {
        const backendExpense = await response.json();
        console.log(`Backend returned: category "${backendExpense.category}"`);
        const frontendCategory = backendToFrontendCategory(backendExpense.category);
        console.log(`Mapped to frontend: "${frontendCategory}"`);
        // Map backend expense_date and category to frontend format
        const newExpense: Expense = {
          id: backendExpense.id,
          amount: backendExpense.amount,
          category: frontendCategory, // Map backend category to frontend
          description: backendExpense.description,
          date: backendExpense.expense_date,
          created_at: backendExpense.created_at,
        };
        setExpenses((prev) => [...prev, newExpense]);
        setExpenseError(null);
      } else {
        const errorData = await response.json().catch(() => ({ detail: "Unknown error" }));
        console.error("Failed to add expense:", errorData);
        setExpenseError(errorData.detail || "Failed to save expense. Please try again.");
        setTimeout(() => setExpenseError(null), 5000);
      }
    } catch (error) {
      console.error("Error adding expense:", error);
    }
  };

  const handleDeleteExpense = async (id: string) => {
    const token = localStorage.getItem("token");
    if (!token) return;

    try {
      const response = await fetch(`${API_URL}/api/expenses/${id}`, {
        method: "DELETE",
        headers: {
          "Authorization": `Bearer ${token}`,
        },
      });

      if (response.status === 401) {
        forceLogout();
        return;
      }

      if (response.ok) {
        setExpenses((prev) => prev.filter((expense) => expense.id !== id));
      } else {
        console.error("Failed to delete expense");
      }
    } catch (error) {
      console.error("Error deleting expense:", error);
    }
  };

  const handleUpdateBudget = (newBudget: number) => {
    setBudget(newBudget);
  };

  const handleLogin = async (username: string, token: string, userId: string) => {
    setUsername(username);
    setIsAuthenticated(true);
    
    // Force scroll to top immediately after login
    window.scrollTo({ top: 0, behavior: "auto" });
    
    // Fetch user profile to get selected_pet
    try {
      const response = await fetch(`${API_URL}/api/user/profile`, {
        headers: {
          "Authorization": `Bearer ${token}`,
        },
      });
      
      if (response.ok) {
        const profile = await response.json();
        if (profile.selected_pet) {
          setSelectedPet(profile.selected_pet as 'penguin' | 'dragon' | 'capybara' | 'cat');
          localStorage.setItem('selectedPet', profile.selected_pet);
        }
      }
    } catch (error) {
      console.error("Failed to fetch user profile:", error);
      // Continue with default pet if profile fetch fails
    }
    
    // Expenses will be fetched by the useEffect that watches isAuthenticated
    
    // Ensure page stays at top after components mount
    setTimeout(() => {
      window.scrollTo({ top: 0, behavior: "auto" });
    }, 0);
  };

  const handleLogout = () => {
    forceLogout();
  };

  // Show login if not authenticated
  if (!isAuthenticated) {
    return <Login onLogin={handleLogin} />;
  }

  // Calculate totals
  const totalSpent = expenses.reduce(
    (sum, expense) => sum + expense.amount,
    0,
  );

  const categoryTotals = expenses.reduce(
    (acc, expense) => {
      acc[expense.category] =
        (acc[expense.category] || 0) + expense.amount;
      return acc;
    },
    {} as { [key: string]: number },
  );

  return (
    <div className="min-h-screen bg-cyan-100 pb-8 relative">
      {/* Dynamic Background with Smooth Transition */}
      <div
        className="fixed inset-0 z-0 transition-opacity duration-700"
        style={{
          backgroundImage: `url(${selectedPet === 'penguin' ? snowyBackground : selectedPet === 'dragon' ? dragonBackground : selectedPet === 'capybara' ? capybaraBackground : catBackground})`,
          backgroundSize: "cover",
          backgroundPosition: "center",
          backgroundAttachment: "fixed",
        }}
      >
        {/* Overlay for better readability */}
        <div className="absolute inset-0 bg-white/40 backdrop-blur-[2px]" />
      </div>

      {/* Content */}
      <div className="relative z-10">
        {/* Header */}
        <header className={`bg-white/90 backdrop-blur-md border-b ${
          selectedPet === 'penguin' ? 'border-cyan-300' : 
          selectedPet === 'dragon' ? 'border-purple-300' : 
          selectedPet === 'capybara' ? 'border-green-300' : 
          'border-pink-300'
        } sticky top-0 z-20 shadow-sm transition-colors duration-500`}>
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3 sm:py-4">
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2 sm:gap-3">
                <div className={`${
                  selectedPet === 'penguin' ? 'bg-gradient-to-br from-cyan-500 to-blue-500' : 
                  selectedPet === 'dragon' ? 'bg-gradient-to-br from-purple-500 to-pink-500' : 
                  selectedPet === 'capybara' ? 'bg-gradient-to-br from-green-500 to-lime-500' : 
                  'bg-gradient-to-br from-pink-500 to-red-500'
                } p-1.5 sm:p-2 rounded-xl sm:rounded-2xl shadow-lg transition-all duration-500`}>
                  <Sparkles className="h-5 w-5 sm:h-6 sm:w-6 text-white" />
                </div>
                <div>
                  <h1 className={`text-xl sm:text-2xl font-bold ${
                    selectedPet === 'penguin' ? 'bg-gradient-to-r from-cyan-600 to-blue-600' : 
                    selectedPet === 'dragon' ? 'bg-gradient-to-r from-purple-600 to-pink-600' : 
                    selectedPet === 'capybara' ? 'bg-gradient-to-r from-green-600 to-lime-600' : 
                    'bg-gradient-to-r from-pink-600 to-red-600'
                  } bg-clip-text text-transparent transition-all duration-500`}>
                    Budget Buddy
                  </h1>
                  <p className="text-xs sm:text-sm text-gray-600 hidden sm:block">
                    Welcome, {username}!
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <BudgetSettings
                  currentBudget={budget}
                  onUpdateBudget={handleUpdateBudget}
                />
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleLogout}
                  className="flex items-center gap-1"
                >
                  <LogOut className="h-4 w-4" />
                  <span className="hidden sm:inline">Logout</span>
                </Button>
              </div>
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 sm:py-8">
          <div className="space-y-4 sm:space-y-6">
            {/* Main Grid Layout */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-6">
              {/* Penny the Penguin - First on mobile, right column on desktop */}
              <div className="lg:col-span-1 lg:order-2">
                <BudgetBuddy
                  totalSpent={totalSpent}
                  budget={budget}
                  recentExpenses={expenses.slice(-5)}
                  categoryTotals={categoryTotals}
                />
              </div>

              {/* Left Column - Budget Summary, Form & Expenses (2 columns on desktop) */}
              <div className="lg:col-span-2 lg:order-1 space-y-4 sm:space-y-6">
                {/* Budget Summary */}
                <BudgetSummary
                  totalSpent={totalSpent}
                  budget={budget}
                  categories={categoryTotals}
                  onUpdateBudget={handleUpdateBudget}
                />
                
                <SpendingForm onAddExpense={handleAddExpense} />
                {expenseError && (
                  <div className="bg-red-100 border border-red-400 text-red-800 px-4 py-3 rounded-lg text-sm">
                    ⚠️ {expenseError}
                  </div>
                )}
                <SpendingGraph 
                  expenses={expenses}
                  budget={budget}
                  categoryTotals={categoryTotals}
                />
                <SpendingCalendar expenses={expenses} />
                <ExpenseList
                  expenses={expenses}
                  onDeleteExpense={handleDeleteExpense}
                />
              </div>
            </div>

            <PetCafe />

            {/* Companion Selector at the Bottom */}
            <CompanionSelector />
          </div>
        </main>
      </div>
    </div>
  );
}