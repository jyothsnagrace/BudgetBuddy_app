import { useState, useRef, useEffect } from 'react';
import { Plus, Calendar as CalendarIcon, Sparkles, Camera } from 'lucide-react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Popover, PopoverContent, PopoverTrigger } from './ui/popover';
import { Calendar } from './ui/calendar';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { Textarea } from './ui/textarea';
import { format } from 'date-fns';
import { cn } from './ui/utils';
import { API_URL } from '../../config';

interface SpendingFormProps {
  onAddExpense: (expense: {
    amount: number;
    category: string;
    description: string;
    date: string;
  }) => void;
}

const categories = [
  '🍕 Food',
  '🏠 Housing',
  '🚗 Transportation',
  '🎮 Entertainment',
  '🛍️ Shopping',
  '💊 Healthcare',
  '📚 Education',
  '💰 Other'
];

export function SpendingForm({ onAddExpense }: SpendingFormProps) {
  // Manual entry state
  const [amount, setAmount] = useState('');
  const [category, setCategory] = useState('');
  const [description, setDescription] = useState('');
  const [date, setDate] = useState<Date>(new Date());
  const [isCalendarOpen, setIsCalendarOpen] = useState(false);
  
  // Quick add state
  const [quickText, setQuickText] = useState('');
  const [isParsingQuick, setIsParsingQuick] = useState(false);
  
  // Receipt state
  const [receiptImage, setReceiptImage] = useState<File | null>(null);
  const [receiptPreview, setReceiptPreview] = useState<string | null>(null);
  
  // Tab control - Default to Manual Entry
  const [activeTab, setActiveTab] = useState('manual');
  
  // Refs for focus management
  const manualFormRef = useRef<HTMLDivElement>(null);
  const quickInputRef = useRef<HTMLTextAreaElement>(null);
  
  // Focus on manual tab on mount
  useEffect(() => {
    if (activeTab === 'manual' && manualFormRef.current) {
      const firstInput = manualFormRef.current.querySelector('input');
      if (firstInput) {
        (firstInput as HTMLInputElement).focus({ preventScroll: true });
      }
    }
  }, [activeTab]);

  const handleManualSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (amount && category) {
      // Convert date to local YYYY-MM-DD format without timezone shift
      const localDate = date.getFullYear() + '-' +
        String(date.getMonth() + 1).padStart(2, '0') + '-' +
        String(date.getDate()).padStart(2, '0');
      
      onAddExpense({
        amount: parseFloat(amount),
        category,
        description,
        date: localDate
      });
      
      // Reset form without scrolling
      setAmount('');
      setCategory('');
      setDescription('');
      setDate(new Date());
      
      // Prevent page scroll
      window.scrollTo({ top: window.scrollY, behavior: 'auto' });
    }
  };


  const handleDateSelect = (selectedDate: Date | undefined) => {
    if (selectedDate) {
      setDate(selectedDate);
      setIsCalendarOpen(false);
    }
  };
  
  // Quick Add: Parse natural language or receipt
  const handleParseQuickAdd = async () => {
    // Check if we have receipt or text
    if (!quickText.trim() && !receiptImage) return;
    
    // Get auth token
    const token = localStorage.getItem("token");
    if (!token) {
      alert('Please log in to use this feature.');
      return;
    }
    
    setIsParsingQuick(true);
    
    try {
      let parsed;
      
      // If receipt image exists, parse receipt
      if (receiptImage) {
        const formData = new FormData();
        formData.append('file', receiptImage);
        
        const response = await fetch(`${API_URL}/api/parse-receipt`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`
          },
          body: formData
        });
        
        if (!response.ok) {
          const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
          throw new Error(errorData.detail || 'Failed to parse receipt');
        }
        const data = await response.json();
        parsed = data.parsed_data;
      } 
      // Otherwise parse text
      else if (quickText.trim()) {
        const response = await fetch(`${API_URL}/api/parse-expense`, {
          method: 'POST',
          headers: { 
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({ text: quickText })
        });
        
        if (!response.ok) {
          const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
          throw new Error(errorData.detail || 'Failed to parse expense');
        }
        const data = await response.json();
        parsed = data.parsed_data;
      }
      
      if (parsed) {
        // Fill manual form with parsed data
        setAmount(parsed.amount.toString());
        setCategory(mapCategoryToEmoji(parsed.category));
        setDescription(parsed.description || '');
        
        // Parse date without timezone issues
        // parsed.date is already in YYYY-MM-DD format from backend
        const [year, month, day] = parsed.date.split('-').map(Number);
        setDate(new Date(year, month - 1, day));
        
        // Clear inputs
        setQuickText('');
        setReceiptImage(null);
        setReceiptPreview(null);
        
        // Switch to manual tab and focus
        setActiveTab('manual');
        
        // Focus on manual form
        setTimeout(() => {
          if (manualFormRef.current) {
            const firstInput = manualFormRef.current.querySelector('input');
            if (firstInput) (firstInput as HTMLInputElement).focus({ preventScroll: true });
          }
        }, 100);
      }
      
    } catch (error) {
      console.error('Parse error:', error);
      const errorMessage = error instanceof Error ? error.message : 'Failed to parse expense. Please try again or use manual entry.';
      alert(errorMessage);
    } finally {
      setIsParsingQuick(false);
    }
  };
  
  // Receipt Photo: Upload handler
  const handleReceiptUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    setReceiptImage(file);
    
    // Create preview
    const reader = new FileReader();
    reader.onload = (event) => {
      setReceiptPreview(event.target?.result as string);
    };
    reader.readAsDataURL(file);
  };
  
  // Helper: Map backend category to emoji category
  const mapCategoryToEmoji = (category: string): string => {
    const mapping: Record<string, string> = {
      'Food': '� Food',
      'Transportation': '🚗 Transportation',
      'Entertainment': '🎮 Entertainment',
      'Shopping': '🛍️ Shopping',
      'Bills': '🏠 Housing',
      'Healthcare': '💊 Healthcare',
      'Education': '📚 Education',
      'Other': '💰 Other'
    };
    return mapping[category] || '💰 Other';
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base sm:text-lg">Add New Expense</CardTitle>
      </CardHeader>
      <CardContent>
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-2 mb-4">
            <TabsTrigger value="quick" className="text-xs sm:text-sm">
              <Sparkles className="w-4 h-4 mr-1" />
              Quick Add
            </TabsTrigger>
            <TabsTrigger value="manual" className="text-xs sm:text-sm">
              <Plus className="w-4 h-4 mr-1" />
              Manual Entry
            </TabsTrigger>
          </TabsList>
          
          {/* Quick Add Tab */}
          <TabsContent value="quick" className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="quick-input">Type naturally or upload receipt 📄 🖼️</Label>
              <Textarea
                id="quick-input"
                ref={quickInputRef}
                placeholder='Try: "I spent 45 dollars on pizza" or "Paid $30 for uber today"'
                value={quickText}
                onChange={(e) => setQuickText(e.target.value)}
                rows={3}
                className="resize-none"
              />
            </div>
            
            <div className="flex items-center gap-3">
              <div className="flex-grow">
                <Label htmlFor="receipt-upload" className="cursor-pointer">
                  <div className="flex items-center gap-2 px-4 py-2 border-2 border-dashed rounded-lg hover:bg-gray-50 transition-colors">
                    <Camera className="w-4 h-4" />
                    <span className="text-sm">{receiptImage ? receiptImage.name : 'Upload Receipt'}</span>
                  </div>
                </Label>
                <Input
                  id="receipt-upload"
                  type="file"
                  accept="image/*"
                  onChange={handleReceiptUpload}
                  className="hidden"
                />
              </div>
              
              <Button
                onClick={handleParseQuickAdd}
                disabled={(!quickText.trim() && !receiptImage) || isParsingQuick}
                className="bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600"
              >
                {isParsingQuick ? (
                  <>Parsing...</>
                ) : (
                  <>
                    <Sparkles className="mr-2 h-4 w-4" />
                    Parse & Fill
                  </>
                )}
              </Button>
            </div>
            
            {receiptPreview && (
              <div className="relative">
                <img 
                  src={receiptPreview} 
                  alt="Receipt preview" 
                  className="w-full max-h-48 object-contain rounded-lg border"
                />
              </div>
            )}
            
            <p className="text-xs text-gray-500 text-center">
              💡 Upload a receipt or type naturally, then parse to auto-fill the form
            </p>
          </TabsContent>
          
          {/* Manual Entry Tab */}
          <TabsContent value="manual" className="space-y-4">
            <form onSubmit={handleManualSubmit} className="space-y-4" ref={manualFormRef}>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="amount">Amount</Label>
                  <Input
                    id="amount"
                    type="number"
                    step="0.01"
                    placeholder="0.00"
                    value={amount}
                    onChange={(e) => setAmount(e.target.value)}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="category">Category</Label>
                  <Select value={category} onValueChange={setCategory} required>
                    <SelectTrigger id="category">
                      <SelectValue placeholder="Select category" />
                    </SelectTrigger>
                    <SelectContent>
                      {categories.map((cat) => (
                        <SelectItem key={cat} value={cat}>{cat}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="description">Description (optional)</Label>
                <Input
                  id="description"
                  type="text"
                  placeholder="What did you buy?"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="date">Date</Label>
                <Popover open={isCalendarOpen} onOpenChange={setIsCalendarOpen}>
                  <PopoverTrigger asChild>
                    <Button
                      id="date"
                      variant="outline"
                      className={cn(
                        "w-full justify-start text-left font-normal",
                        !date && "text-muted-foreground"
                      )}
                      type="button"
                    >
                      <CalendarIcon className="mr-2 h-4 w-4" />
                      {date ? format(date, 'PPP') : <span>Pick a date</span>}
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent className="w-auto p-0 bg-white" align="start">
                    <Calendar
                      mode="single"
                      selected={date}
                      onSelect={handleDateSelect}
                      initialFocus
                    />
                  </PopoverContent>
                </Popover>
              </div>
              <Button 
                type="submit" 
                className="w-full bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600"
              >
                <Plus className="mr-2 h-4 w-4" />
                Add Expense
              </Button>
            </form>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}