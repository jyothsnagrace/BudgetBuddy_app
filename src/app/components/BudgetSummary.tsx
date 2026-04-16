import { DollarSign, TrendingUp, TrendingDown, Edit2, Check, X } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { useState } from 'react';

interface BudgetSummaryProps {
  totalSpent: number;
  budget: number;
  categories: { [key: string]: number };
  onUpdateBudget?: (newBudget: number) => void;
}

export function BudgetSummary({ totalSpent, budget, categories, onUpdateBudget }: BudgetSummaryProps) {
  const remaining = budget - totalSpent;
  const percentSpent = budget > 0 ? (totalSpent / budget) * 100 : 0;
  const [isEditing, setIsEditing] = useState(false);
  const [newBudget, setNewBudget] = useState(budget.toString());

  const handleEdit = () => {
    setIsEditing(true);
    setNewBudget(budget.toString());
  };

  const handleSave = () => {
    const budgetValue = parseFloat(newBudget);
    if (onUpdateBudget && !isNaN(budgetValue) && budgetValue > 0) {
      onUpdateBudget(budgetValue);
      setIsEditing(false);
    }
  };

  const handleCancel = () => {
    setIsEditing(false);
    setNewBudget(budget.toString());
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSave();
    } else if (e.key === 'Escape') {
      handleCancel();
    }
  };

  return (
    <div className="grid gap-3 sm:gap-4 grid-cols-1 sm:grid-cols-3">
      <Card className="bg-white/85 backdrop-blur-md border-2 border-purple-300 shadow-lg">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Total Budget</CardTitle>
          <DollarSign className="h-4 w-4 text-purple-600" />
        </CardHeader>
        <CardContent>
          {isEditing ? (
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <span className="text-xl font-bold text-purple-900">$</span>
                <input
                  type="number"
                  value={newBudget}
                  onChange={(e) => setNewBudget(e.target.value)}
                  onKeyDown={handleKeyDown}
                  autoFocus
                  className="text-xl sm:text-2xl font-bold text-purple-900 border-b-2 border-purple-400 focus:border-purple-600 outline-none bg-transparent w-full"
                  placeholder="Enter budget"
                />
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={handleSave}
                  className="flex items-center gap-1 px-3 py-1 bg-green-500 hover:bg-green-600 text-white text-xs rounded-lg transition-colors"
                >
                  <Check className="h-3 w-3" />
                  Save
                </button>
                <button
                  onClick={handleCancel}
                  className="flex items-center gap-1 px-3 py-1 bg-gray-400 hover:bg-gray-500 text-white text-xs rounded-lg transition-colors"
                >
                  <X className="h-3 w-3" />
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-between">
              <div className="text-xl sm:text-2xl font-bold text-purple-900">${budget.toFixed(2)}</div>
              {onUpdateBudget && (
                <button
                  onClick={handleEdit}
                  className="p-1.5 hover:bg-purple-100 rounded-lg transition-colors group"
                  title="Edit budget"
                >
                  <Edit2 className="h-4 w-4 text-purple-600 group-hover:text-purple-800" />
                </button>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      <Card className="bg-white/85 backdrop-blur-md border-2 border-orange-300 shadow-lg">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Total Spent</CardTitle>
          <TrendingUp className="h-4 w-4 text-orange-600" />
        </CardHeader>
        <CardContent>
          <div className="text-xl sm:text-2xl font-bold text-orange-900">${totalSpent.toFixed(2)}</div>
          <div className="text-xs text-orange-700 mt-1">{percentSpent.toFixed(1)}% of budget</div>
        </CardContent>
      </Card>

      <Card className={`bg-white/85 backdrop-blur-md shadow-lg border-2 ${remaining >= 0 ? 'border-green-300' : 'border-red-300'}`}>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Remaining</CardTitle>
          {remaining >= 0 ? (
            <TrendingDown className="h-4 w-4 text-green-600" />
          ) : (
            <TrendingUp className="h-4 w-4 text-red-600" />
          )}
        </CardHeader>
        <CardContent>
          <div className={`text-xl sm:text-2xl font-bold ${remaining >= 0 ? 'text-green-900' : 'text-red-900'}`}>
            ${Math.abs(remaining).toFixed(2)}
          </div>
          {remaining < 0 && <div className="text-xs text-red-700 mt-1">Over budget!</div>}
        </CardContent>
      </Card>
    </div>
  );
}